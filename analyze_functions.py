#!/usr/bin/env python3
"""Script to analyze Python files and find functions longer than 50 lines."""

import ast
from pathlib import Path
from typing import List, Tuple


def count_function_lines(node: ast.FunctionDef) -> int:
    """Count the number of lines in a function definition."""
    if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
        return 0
    if node.end_lineno is None:
        return 0
    return node.end_lineno - node.lineno + 1


def analyze_file(filepath: Path) -> List[Tuple[str, int, int]]:
    """Analyze a Python file and return functions longer than 50 lines.

    Returns:
        List of tuples: (function_name, start_line, line_count)
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(filepath))
        long_functions = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                line_count = count_function_lines(node)  # type: ignore[arg-type]
                if line_count > 50:
                    long_functions.append((node.name, node.lineno, line_count))

        return long_functions
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return []


def main():
    """Analyze all Python files in modbuspython for functions longer than 50 lines."""
    modbuspython_dir = Path("modbuspython")

    # Exclude directories
    exclude_dirs = {"__pycache__", "tests", "examples", "migrations", "assets", "BannerISS", "ico"}

    results = {}

    for py_file in modbuspython_dir.rglob("*.py"):
        # Skip excluded directories
        if any(excluded in py_file.parts for excluded in exclude_dirs):
            continue

        long_functions = analyze_file(py_file)
        if long_functions:
            results[str(py_file)] = long_functions

    # Print results
    if results:
        print("=" * 80)
        print("FUNCTIONS LONGER THAN 50 LINES")
        print("=" * 80)
        total_functions = 0
        for filepath, functions in sorted(results.items()):
            print(f"\n{filepath}:")
            for func_name, start_line, line_count in functions:
                print(f"  - {func_name}() at line {start_line}: {line_count} lines")
                total_functions += 1
        print(f"\n{'=' * 80}")
        print(f"Total: {total_functions} functions need refactoring")
        print("=" * 80)
    else:
        print("No functions longer than 50 lines found!")


if __name__ == "__main__":
    main()
