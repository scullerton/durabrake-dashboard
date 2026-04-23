"""
QuickBooks Online client for the monthly automation.

Pulls two reports via the QBO Reports API and saves them as Excel files
matching the existing fuzzy-match filenames:
    - SalesByCustomerDetail  -> DuraBrake_Sales by Customer Detail.xlsx
    - CustomerIncome         -> DuraBrake_Income by Customer Summary.xlsx

Authentication — SHARED WITH DB Financial Analysis:
    This project reads OAuth credentials from:
        C:\\Users\\scull\\Documents\\ClaudeCodeWorkspace\\DB Financial Analysis\\
            config.json   (client_id, client_secret, environment)
            tokens.json   (refresh_token, realm_id — rotates on each refresh)

    Intuit rotates the refresh token on every refresh, and only the most
    recent one is valid. Pointing both projects at the same tokens.json
    keeps them in lockstep and avoids "invalid_grant" failures.

Reports API reference:
    https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/reports
"""

from __future__ import annotations

import argparse
import calendar
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# Shared OAuth credentials with DB Financial Analysis project — single source
# of truth for the QBO refresh token (Intuit rotates it on every use).
QBO_CONFIG_DIR = Path(r"C:\Users\scull\Documents\ClaudeCodeWorkspace\DB Financial Analysis")
QBO_CONFIG_FILE = QBO_CONFIG_DIR / "config.json"
QBO_TOKENS_FILE = QBO_CONFIG_DIR / "tokens.json"

QBO_BASE_URL = {
    "production": "https://quickbooks.api.intuit.com/v3",
    "sandbox": "https://sandbox-quickbooks.api.intuit.com/v3",
}
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"


# ────────────────────────────────────────────────────────────────────────
# Shared credential loading
# ────────────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    if not QBO_CONFIG_FILE.exists():
        raise RuntimeError(
            f"QBO config not found at {QBO_CONFIG_FILE}. "
            f"The DB Financial Analysis project is the authoritative source."
        )
    return json.loads(QBO_CONFIG_FILE.read_text())


def _load_tokens() -> dict:
    if not QBO_TOKENS_FILE.exists():
        raise RuntimeError(
            f"QBO tokens not found at {QBO_TOKENS_FILE}. "
            f"Run the initial OAuth flow in the DB Financial Analysis project."
        )
    return json.loads(QBO_TOKENS_FILE.read_text())


def _save_tokens(tokens: dict) -> None:
    """Write rotated tokens back to the shared file atomically."""
    tokens["saved_at"] = time.time()
    tmp = QBO_TOKENS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(tokens, indent=2))
    tmp.replace(QBO_TOKENS_FILE)


# ────────────────────────────────────────────────────────────────────────
# OAuth — token refresh
# ────────────────────────────────────────────────────────────────────────

def _refresh_access_token() -> str:
    """Exchange the stored refresh token for a fresh access token.

    Intuit rotates the refresh token on every refresh — we write the
    rotated token back to the shared tokens.json so DB Financial Analysis
    stays in sync.
    """
    config = _load_config()
    tokens = _load_tokens()

    # Short-circuit if the current access token is still fresh (with 60s buffer)
    if tokens.get("expires_at", 0) > time.time() + 60 and tokens.get("access_token"):
        return tokens["access_token"]

    resp = requests.post(
        TOKEN_URL,
        auth=(config["client_id"], config["client_secret"]),
        data={"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"]},
        headers={"Accept": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()

    now = time.time()
    tokens["access_token"] = payload["access_token"]
    tokens["expires_in"] = payload.get("expires_in", 3600)
    tokens["expires_at"] = now + tokens["expires_in"]
    if payload.get("refresh_token"):
        tokens["refresh_token"] = payload["refresh_token"]
        tokens["refresh_token_expires_at"] = now + payload.get("x_refresh_token_expires_in", 8726400)
    _save_tokens(tokens)

    return tokens["access_token"]


# ────────────────────────────────────────────────────────────────────────
# Reports API — fetch + flatten
# ────────────────────────────────────────────────────────────────────────

def _period_dates(period: str) -> tuple[str, str]:
    """Return (start_date, end_date) as ISO strings for a given YY.MM period."""
    yy, mm = period.split(".")
    year, month = 2000 + int(yy), int(mm)
    last_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"


def _flatten_qbo_report(report_json: dict) -> pd.DataFrame:
    """Flatten QBO's nested report JSON into a DataFrame.

    QBO reports return rows structured as Header → nested Rows → summary rows.
    We walk the tree recursively and emit one dict per ColData row, tagging
    rows with the header/section they belong to so groupings are preserved.
    """
    columns = [c["ColTitle"] for c in report_json["Columns"]["Column"]]
    out_rows: list[dict] = []

    def walk(rows_container: list, section: str = ""):
        for row in rows_container:
            row_type = row.get("type")
            if row_type == "Section":
                header = row.get("Header", {}).get("ColData", [{}])[0].get("value", section)
                walk(row.get("Rows", {}).get("Row", []), header)
                # Section summary row (totals) — include if present
                summary = row.get("Summary", {}).get("ColData")
                if summary:
                    out_rows.append({"_section": header, "_row_type": "Total",
                                     **{columns[i]: c.get("value", "") for i, c in enumerate(summary)}})
            else:
                col_data = row.get("ColData", [])
                if col_data:
                    out_rows.append({"_section": section, "_row_type": row_type or "Data",
                                     **{columns[i]: c.get("value", "") for i, c in enumerate(col_data)}})

    walk(report_json.get("Rows", {}).get("Row", []))
    return pd.DataFrame(out_rows)


def _call_report(report_name: str, params: dict) -> dict:
    """Low-level GET against /reports/{name}."""
    tokens = _load_tokens()
    config = _load_config()
    realm_id = tokens["realm_id"]
    environment = config.get("environment", "production")
    access_token = _refresh_access_token()

    url = f"{QBO_BASE_URL[environment]}/company/{realm_id}/reports/{report_name}"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        params=params,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def _query_entities(entity: str, where: str, batch_size: int = 1000) -> list[dict]:
    """Paginate through a SQL-like QBO query. Mirrors DB Financial Analysis/qbo_client.query()."""
    tokens = _load_tokens()
    config = _load_config()
    realm_id = tokens["realm_id"]
    environment = config.get("environment", "production")
    access_token = _refresh_access_token()
    base_url = f"{QBO_BASE_URL[environment]}/company/{realm_id}/query"

    all_results: list[dict] = []
    start_position = 1
    while True:
        q = f"SELECT * FROM {entity} WHERE {where} STARTPOSITION {start_position} MAXRESULTS {batch_size}"
        resp = requests.get(
            base_url,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            params={"query": q},
            timeout=60,
        )
        resp.raise_for_status()
        qr = resp.json().get("QueryResponse", {})
        batch = qr.get(entity, [])
        if not batch:
            break
        all_results.extend(batch)
        if len(batch) < batch_size:
            break
        start_position += batch_size
    return all_results


def fetch_sales_by_customer_detail(period: str, dest_folder: str) -> str:
    """Emulate QBO's "Sales by Customer Detail" report by querying Invoice +
    CreditMemo entities directly and expanding each transaction's line items.

    Produces an Excel file whose positional column layout matches what
    scripts/customer_analysis.py::parse_customer_sales_data() expects:
        [customer_section], Transaction date, Transaction type, Num,
        Product/Service full name, Memo/Description, Quantity, Sales price,
        Amount, Balance
    Customer rows act as section headers (col 0 populated, col 1 NaN).
    Date window = trailing 12 months ending on the last day of `period`
    (matches the historical L12M export used by the existing pipeline).
    """
    yy, mm = period.split(".")
    year, month = 2000 + int(yy), int(mm)
    last_day = calendar.monthrange(year, month)[1]
    end_date = f"{year:04d}-{month:02d}-{last_day:02d}"
    # Trailing 12 months — match existing Excel export window
    l12m_start_month = month + 1
    l12m_start_year = year - 1
    if l12m_start_month > 12:
        l12m_start_month -= 12
        l12m_start_year += 1
    start_date = f"{l12m_start_year:04d}-{l12m_start_month:02d}-01"

    print(f"  Fetching Invoice + CreditMemo {start_date}..{end_date}")
    where_clause = f"TxnDate >= '{start_date}' AND TxnDate <= '{end_date}'"
    invoices = _query_entities("Invoice", where_clause)
    credit_memos = _query_entities("CreditMemo", where_clause)
    print(f"  {len(invoices)} invoices, {len(credit_memos)} credit memos")

    # Expand into one row per line, tag with customer + transaction type
    all_rows: list[dict] = []
    for txn, ttype in [(invoices, "Invoice"), (credit_memos, "Credit Memo")]:
        for t in txn:
            customer = t.get("CustomerRef", {}).get("name", "Unknown")
            tx_date = t.get("TxnDate", "")
            doc_num = t.get("DocNumber", "")
            balance = t.get("Balance", t.get("TotalAmt", 0))
            sign = -1 if ttype == "Credit Memo" else 1
            for line in t.get("Line", []):
                detail = line.get("SalesItemLineDetail") or line.get("DescriptionOnly") or {}
                item_ref = detail.get("ItemRef", {}) if isinstance(detail, dict) else {}
                product = item_ref.get("name", "") if item_ref else ""
                description = line.get("Description", "")
                qty = (detail.get("Qty") if isinstance(detail, dict) else None) or ""
                unit_price = (detail.get("UnitPrice") if isinstance(detail, dict) else None) or ""
                amount = line.get("Amount", 0) * sign
                # Skip subtotal and non-financial line types
                if line.get("DetailType") in ("SubTotalLineDetail",):
                    continue
                all_rows.append({
                    "customer": customer,
                    "Transaction date": tx_date,
                    "Transaction type": ttype,
                    "Num": doc_num,
                    "Product/Service full name": product,
                    "Memo/Description": description,
                    "Quantity": qty,
                    "Sales price": unit_price,
                    "Amount": amount,
                    "Balance": balance,
                })

    # Build the positional Excel shape customer_analysis.py parses
    out_rows: list[list] = []
    header_block = [
        ["Sales by Customer Detail"] + [None] * 9,
        ["DuraBrake"] + [None] * 9,
        [f"{calendar.month_name[l12m_start_month]}, {l12m_start_year}-"
         f"{calendar.month_name[month]}, {year}"] + [None] * 9,
        [None] * 10,
        [None, "Transaction date", "Transaction type", "Num",
         "Product/Service full name", "Memo/Description",
         "Quantity", "Sales price", "Amount", "Balance"],
    ]
    out_rows.extend(header_block)

    import pandas as _pd
    sorted_rows = sorted(all_rows, key=lambda r: (r["customer"], r["Transaction date"]))
    current = None
    for r in sorted_rows:
        if r["customer"] != current:
            out_rows.append([r["customer"]] + [None] * 9)
            current = r["customer"]
        out_rows.append([None, r["Transaction date"], r["Transaction type"], r["Num"],
                         r["Product/Service full name"], r["Memo/Description"],
                         r["Quantity"], r["Sales price"], r["Amount"], r["Balance"]])

    df = _pd.DataFrame(out_rows)
    dest = os.path.join(dest_folder, "DuraBrake_Sales by Customer Detail.xlsx")
    df.to_excel(dest, index=False, header=False)
    print(f"  -> {dest}  ({len(out_rows)} rows, {len(sorted_rows)} transaction lines)")
    return dest


def fetch_income_by_customer_summary(period: str, dest_folder: str) -> str:
    """Pull QBO's CustomerIncome report and save as Excel in the exact shape
    that scripts/customer_analysis.py::load_customer_income_data() expects:

        skiprows=3, then column order: customer | income | expenses | net_income

    The existing Excel has a 3-line banner (title/org/date-range) then the
    header row, then data rows — we mirror that exactly.
    """
    # Historical convention: the Income by Customer report is L12M (same
    # trailing-12-month window as Sales Detail), not single-month.
    yy, mm = period.split(".")
    year, month = 2000 + int(yy), int(mm)
    last_day = calendar.monthrange(year, month)[1]
    end_date = f"{year:04d}-{month:02d}-{last_day:02d}"
    l12m_start_month = month + 1
    l12m_start_year = year - 1
    if l12m_start_month > 12:
        l12m_start_month -= 12
        l12m_start_year += 1
    start_date = f"{l12m_start_year:04d}-{l12m_start_month:02d}-01"

    print(f"  Fetching CustomerIncome {start_date}..{end_date}")
    report = _call_report("CustomerIncome", {
        "start_date": start_date, "end_date": end_date, "accounting_method": "Accrual",
    })

    # Extract (customer, income, expenses, net_income) tuples from QBO's nested rows
    flat = _flatten_qbo_report(report)
    # The flattened frame has _section, _row_type, and the native columns.
    # Native columns vary by tenant — typically ['', 'Income', 'Expenses', 'Net Income']
    # where the first column holds the customer name on Data rows.
    data_rows = flat[flat["_row_type"] == "Data"].copy()
    # Customer name lives in the first non-underscore column
    native_cols = [c for c in flat.columns if not c.startswith("_")]
    if len(native_cols) < 4:
        raise RuntimeError(f"Unexpected CustomerIncome shape: columns={native_cols}")
    name_col, income_col, expense_col, net_col = native_cols[0], native_cols[1], native_cols[2], native_cols[3]

    records = data_rows[[name_col, income_col, expense_col, net_col]].values.tolist()

    # Build positional Excel shape (3 banner rows + header + data)
    import pandas as _pd
    out_rows = [
        ["Income by Customer Summary", None, None, None],
        ["DuraBrake", None, None, None],
        [f"{calendar.month_name[l12m_start_month]}, {l12m_start_year}-"
         f"{calendar.month_name[month]}, {year}", None, None, None],
        ["Customer", "Income", "Expenses", "Net income"],
    ]
    out_rows.extend(records)

    df = _pd.DataFrame(out_rows)
    dest = os.path.join(dest_folder, "DuraBrake_Income by Customer Summary.xlsx")
    df.to_excel(dest, index=False, header=False)
    print(f"  -> {dest}  ({len(records)} customers)")
    return dest


def fetch_both(period: str, project_root: str) -> None:
    """Convenience: run both report pulls into inputs/{period}/, skipping any already present."""
    dest_folder = os.path.join(project_root, "inputs", period)
    os.makedirs(dest_folder, exist_ok=True)

    for name, fetcher in [
        ("DuraBrake_Sales by Customer Detail.xlsx", fetch_sales_by_customer_detail),
        ("DuraBrake_Income by Customer Summary.xlsx", fetch_income_by_customer_summary),
    ]:
        existing = os.path.join(dest_folder, name)
        if os.path.exists(existing):
            print(f"[SKIP] {name} already present")
            continue
        fetcher(period, dest_folder)


# ────────────────────────────────────────────────────────────────────────
# Interactive setup (one-time)
# ────────────────────────────────────────────────────────────────────────

def setup() -> None:
    """Verify shared QBO credentials with DB Financial Analysis are readable.

    There's no interactive setup here because credentials are authoritatively
    maintained by the DB Financial Analysis project at:
        C:\\Users\\scull\\Documents\\ClaudeCodeWorkspace\\DB Financial Analysis\\
    """
    print("QuickBooks Online — Credential Check")
    print("=" * 60)
    print(f"Config file: {QBO_CONFIG_FILE}")
    print(f"Tokens file: {QBO_TOKENS_FILE}")
    print()

    try:
        config = _load_config()
        tokens = _load_tokens()
        print(f"[OK] Config loaded — realm_id={tokens['realm_id']}, env={config.get('environment')}")
        rt_exp = tokens.get("refresh_token_expires_at", 0)
        if rt_exp:
            days = (rt_exp - time.time()) / 86400
            print(f"[OK] Refresh token valid for ~{days:.0f} more days")
    except Exception as exc:
        print(f"[FAIL] Cannot read credentials: {exc}")
        print("Fix: run the OAuth flow in the DB Financial Analysis project first.")
        sys.exit(1)

    print("\nVerifying by refreshing access token...")
    try:
        _refresh_access_token()
        print("[OK] QBO credentials valid.")
    except Exception as exc:
        print(f"[FAIL] {exc}")
        sys.exit(1)


# ────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QBO client for DuraBrake automation.")
    parser.add_argument("--setup", action="store_true", help="Interactive one-time setup")
    parser.add_argument("--period", help="YY.MM period to fetch")
    parser.add_argument("--project-root",
                        default=str(Path(__file__).resolve().parent.parent),
                        help="Root of KPI Dashboard project")
    parser.add_argument("--test", action="store_true",
                        help="Verify credentials by refreshing the access token")
    args = parser.parse_args()

    if args.setup:
        setup()
    elif args.test:
        token = _refresh_access_token()
        print(f"[OK] Access token obtained ({len(token)} chars). Credentials valid.")
    elif args.period:
        fetch_both(args.period, args.project_root)
    else:
        parser.print_help()
