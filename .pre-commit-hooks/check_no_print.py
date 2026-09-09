#!/usr/bin/env python3
"""Pre-commit hook to check for print() statements in Python files."""

import re
import sys
from pathlib import Path


def check_file(filepath: Path) -> list[tuple[int, str]]:
    """Check a file for print() statements.

    Args:
        filepath: Path to the Python file to check

    Returns:
        List of tuples (line_number, line_content) where print() was found
    """
    violations = []
    pattern = re.compile(r"^\s*print\s*\(")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                # Skip commented lines
                if line.strip().startswith("#"):
                    continue
                # Check for print statement
                if pattern.match(line):
                    violations.append((line_num, line.rstrip()))
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return []

    return violations


def main() -> int:
    """Check all provided files for print statements.

    Returns:
        0 if no violations found, 1 otherwise
    """
    if len(sys.argv) < 2:
        print("Usage: check_no_print.py <file1> <file2> ...", file=sys.stderr)
        return 1

    files_to_check = [Path(f) for f in sys.argv[1:]]
    found_violations = False

    for filepath in files_to_check:
        violations = check_file(filepath)
        if violations:
            found_violations = True
            print(f"\n{filepath}:")
            for line_num, line_content in violations:
                print(f"  Line {line_num}: {line_content}")

    if found_violations:
        print("\n❌ Found print() statements. Please use logging instead.")
        print("   Replace print() with appropriate logging calls:")
        print("   - logger.debug() for debugging information")
        print("   - logger.info() for general information")
        print("   - logger.warning() for warnings")
        print("   - logger.error() for errors")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
