#!/usr/bin/env python3
"""Script to analyze cyclomatic complexity of Python functions."""

import ast
from pathlib import Path
from typing import List, Tuple


class ComplexityAnalyzer(ast.NodeVisitor):
    """AST visitor to calculate cyclomatic complexity."""

    def __init__(self):
        """Initialize with base complexity of 1."""
        self.complexity = 1  # Base complexity

    def visit_If(self, node):
        """Increment complexity for if statements."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        """Increment complexity for while loops."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        """Increment complexity for for loops."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        """Increment complexity for except handlers."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node):
        """Increment complexity for with statements."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node):
        """Increment complexity for assert statements."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        """Increment complexity for boolean operators."""
        # Count 'and' and 'or' operators
        self.complexity += len(node.values) - 1
        self.generic_visit(node)


def calculate_complexity(func_node):
    """Calculate cyclomatic complexity for a function."""
    analyzer = ComplexityAnalyzer()
    analyzer.visit(func_node)
    return analyzer.complexity


def analyze_file(filepath: Path) -> List[Tuple[str, int, int, int]]:
    """Analyze a Python file and return functions with high complexity.

    Returns:
        List of tuples: (function_name, start_line, line_count, complexity)
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(filepath))
        results = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                line_count = (
                    node.end_lineno - node.lineno + 1
                    if hasattr(node, "end_lineno") and node.end_lineno is not None
                    else 0
                )
                complexity = calculate_complexity(node)

                # Report if > 50 lines OR complexity >= 10
                if line_count > 50 or complexity >= 10:
                    results.append((node.name, node.lineno, line_count, complexity))

        return results
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return []


def main():
    """Analyze all Python files in modbuspython for cyclomatic complexity."""
    modbuspython_dir = Path("modbuspython")

    # Exclude directories
    exclude_dirs = {"__pycache__", "tests", "examples", "migrations", "assets", "BannerISS", "ico"}

    results = {}

    for py_file in modbuspython_dir.rglob("*.py"):
        # Skip excluded directories
        if any(excluded in py_file.parts for excluded in exclude_dirs):
            continue

        issues = analyze_file(py_file)
        if issues:
            results[str(py_file)] = issues

    # Print results
    if results:
        print("=" * 90)
        print("FUNCTIONS NEEDING REFACTORING (>50 lines OR complexity >=10)")
        print("=" * 90)
        total_functions = 0
        high_complexity = 0

        for filepath, functions in sorted(results.items()):
            print(f"\n{filepath}:")
            for func_name, start_line, line_count, complexity in functions:
                marker = " ⚠️ HIGH COMPLEXITY" if complexity >= 10 else ""
                print(f"  - {func_name}() at line {start_line}: {line_count} lines, complexity={complexity}{marker}")
                total_functions += 1
                if complexity >= 10:
                    high_complexity += 1

        print(f"\n{'=' * 90}")
        print(f"Total: {total_functions} functions need refactoring")
        print(f"High complexity (>=10): {high_complexity} functions")
        print("=" * 90)
    else:
        print("All functions meet the requirements!")


if __name__ == "__main__":
    main()
