"""
Centralized credential storage for monthly automation.

Wraps the `keyring` library so QBO and FileMaker clients share a single
storage mechanism. On Windows this resolves to the Windows Credential
Manager, which is protected by the logged-in user's Windows credentials
and never touches disk in plaintext.

Service names used across the automation:
    durabrake_qbo  - QuickBooks Online OAuth + realm info
    durabrake_fmp  - FileMaker Cloud Data API credentials

Keys under durabrake_qbo:
    client_id        - Intuit developer app client ID
    client_secret    - Intuit developer app client secret
    refresh_token    - Long-lived OAuth refresh token (100+ days)
    realm_id         - QuickBooks company ID
    environment      - "production" or "sandbox"

Keys under durabrake_fmp:
    host             - FM Cloud hostname (e.g., "mycompany.account.filemaker-cloud.com")
    database         - Database name
    username         - API user
    password         - API password
    backlog_layout   - Layout name that exposes the "ordered but not invoiced" report
"""

import keyring
import getpass
import sys


QBO_SERVICE = "durabrake_qbo"
FMP_SERVICE = "durabrake_fmp"


def get_secret(service: str, key: str, required: bool = True) -> str | None:
    """Read a secret from the OS credential store.

    Args:
        service: One of QBO_SERVICE, FMP_SERVICE.
        key: Field name within the service.
        required: If True, raise when not found. If False, return None.
    """
    value = keyring.get_password(service, key)
    if value is None and required:
        raise RuntimeError(
            f"Missing credential: service='{service}' key='{key}'.\n"
            f"Run the matching setup script first "
            f"(e.g., `python scripts/qbo_client.py --setup`)."
        )
    return value


def set_secret(service: str, key: str, value: str) -> None:
    """Persist a secret to the OS credential store."""
    keyring.set_password(service, key, value)


def prompt_and_store(service: str, key: str, prompt: str, secret: bool = False) -> str:
    """Interactive helper used by setup scripts.

    Shows the current value (masked if `secret`) and prompts for a new one;
    keeps the existing value if the user presses Enter.
    """
    current = keyring.get_password(service, key)
    if current:
        masked = "***" + current[-4:] if secret and len(current) > 4 else current
        prompt_text = f"{prompt} [{masked}]: "
    else:
        prompt_text = f"{prompt}: "

    entry = getpass.getpass(prompt_text) if secret else input(prompt_text)
    entry = entry.strip()

    if not entry:
        if not current:
            print(f"ERROR: {key} is required.", file=sys.stderr)
            sys.exit(1)
        return current

    set_secret(service, key, entry)
    return entry


def delete_secret(service: str, key: str) -> None:
    """Remove a secret — used in credential rotation / testing."""
    try:
        keyring.delete_password(service, key)
    except keyring.errors.PasswordDeleteError:
        pass


if __name__ == "__main__":
    # Simple CLI: `python secrets_helper.py list` shows what's stored (no values).
    import argparse

    parser = argparse.ArgumentParser(description="Inspect automation credentials.")
    parser.add_argument("action", choices=["list", "delete"])
    parser.add_argument("--service", choices=[QBO_SERVICE, FMP_SERVICE])
    parser.add_argument("--key")
    args = parser.parse_args()

    known_keys = {
        QBO_SERVICE: ["client_id", "client_secret", "refresh_token", "realm_id", "environment"],
        FMP_SERVICE: ["host", "database", "username", "password", "backlog_layout"],
    }

    if args.action == "list":
        for svc, keys in known_keys.items():
            print(f"\n{svc}:")
            for k in keys:
                has = keyring.get_password(svc, k) is not None
                print(f"  {k}: {'SET' if has else '(empty)'}")
    elif args.action == "delete":
        if not args.service or not args.key:
            print("ERROR: --service and --key required for delete", file=sys.stderr)
            sys.exit(1)
        delete_secret(args.service, args.key)
        print(f"Deleted {args.service}/{args.key}")
