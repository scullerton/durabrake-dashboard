"""
Shared file utilities for dashboard generation.
Finds input files using keyword matching to handle naming variations.
"""

import os


def find_input_file(folder, keywords, extensions=None):
    """
    Find a single file in folder whose name contains ALL keywords (case-insensitive).

    Args:
        folder: Path to the input folder (e.g., "inputs/26.01")
        keywords: List of strings that must all appear in the filename
        extensions: Optional list of allowed extensions (e.g., [".xlsx", ".csv"]).
                    If None, allows any extension.

    Returns:
        Full path to the matching file.

    Raises:
        FileNotFoundError: If no match or multiple matches found.
    """
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Input folder not found: {folder}")

    all_files = os.listdir(folder)
    matches = []

    for filename in all_files:
        name_lower = filename.lower()

        # Check extension filter
        if extensions:
            _, ext = os.path.splitext(filename)
            if ext.lower() not in [e.lower() for e in extensions]:
                continue

        # Check all keywords present
        if all(kw.lower() in name_lower for kw in keywords):
            matches.append(filename)

    if len(matches) == 0:
        raise FileNotFoundError(
            f"No file matching keywords {keywords} found in {folder}.\n"
            f"Files present: {all_files}"
        )

    if len(matches) > 1:
        raise FileNotFoundError(
            f"Multiple files matching keywords {keywords} in {folder}: {matches}\n"
            f"Please ensure only one matching file exists."
        )

    return os.path.join(folder, matches[0])
