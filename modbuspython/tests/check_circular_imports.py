"""
Circular Import Detection Script for Nexo Solar

This script analyzes the import structure of the modbuspython package
to detect circular dependencies between modules.

Usage:
    python -m modbuspython.tests.check_circular_imports
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class ImportAnalyzer(ast.NodeVisitor):
    """AST visitor to extract import statements from Python files."""

    def __init__(self, module_path: str):
        self.module_path = module_path
        self.imports: List[str] = []

    def visit_Import(self, node: ast.Import):
        """Visit import statements (e.g., import module)."""
        for alias in node.names:
            self.imports.append(alias.name.split(".")[0])
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from-import statements (e.g., from module import x)."""
        if node.module:
            # Extract the top-level module
            module = node.module.split(".")[0]
            self.imports.append(module)
        self.generic_visit(node)


def get_python_files(root_dir: Path) -> List[Path]:
    """Get all Python files in the directory tree."""
    python_files = []
    for path in root_dir.rglob("*.py"):
        # Skip __pycache__ and test files for now
        if "__pycache__" not in str(path):
            python_files.append(path)
    return python_files


def extract_imports(file_path: Path, base_dir: Path) -> Tuple[str, List[str]]:
    """
    Extract imports from a Python file.

    Returns:
        Tuple of (module_name, list_of_imported_modules)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        analyzer = ImportAnalyzer(str(file_path))
        analyzer.visit(tree)

        # Convert file path to module name
        relative_path = file_path.relative_to(base_dir)
        module_parts = list(relative_path.parts[:-1])  # Remove filename
        if relative_path.stem != "__init__":
            module_parts.append(relative_path.stem)

        module_name = ".".join(module_parts) if module_parts else relative_path.stem

        # Filter to only include internal imports (modbuspython modules)
        internal_imports = []
        for imp in analyzer.imports:
            if imp in ["backend", "ui", "config", "data_access", "migrations", "tests"]:
                internal_imports.append(imp)

        return module_name, internal_imports

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return "", []


def build_dependency_graph(root_dir: Path) -> Dict[str, List[str]]:
    """Build a dependency graph of all modules."""
    graph = defaultdict(list)

    python_files = get_python_files(root_dir)

    for file_path in python_files:
        module_name, imports = extract_imports(file_path, root_dir)
        if module_name:
            graph[module_name] = imports

    return dict(graph)


def detect_cycles(graph: Dict[str, List[str]]) -> List[List[str]]:
    """
    Detect circular dependencies using DFS.

    Returns:
        List of cycles found (each cycle is a list of module names)
    """
    cycles = []
    visited = set()
    rec_stack = set()
    path = []

    def dfs(node: str) -> bool:
        """DFS to detect cycles."""
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)
                return True

        path.pop()
        rec_stack.remove(node)
        return False

    for node in graph:
        if node not in visited:
            dfs(node)

    return cycles


def analyze_module_layers(graph: Dict[str, List[str]]) -> Dict[str, Set[str]]:
    """
    Analyze which layers each module belongs to and what it imports.

    Returns:
        Dictionary mapping layer names to sets of modules
    """
    layers = {"ui": set(), "backend": set(), "data_access": set(), "config": set(), "migrations": set(), "tests": set()}

    for module in graph.keys():
        for layer in layers.keys():
            if module.startswith(layer):
                layers[layer].add(module)
                break

    return layers


def check_layer_violations(graph: Dict[str, List[str]]) -> List[str]:
    """
    Check for architectural layer violations.

    Rules:
    - UI can import from backend, config
    - Backend can import from data_access, config
    - Data_access can import from config only
    - Config should not import from other layers
    """
    violations = []

    for module, imports in graph.items():
        # Determine module's layer
        module_layer = None
        for layer in ["ui", "backend", "data_access", "config", "migrations", "tests"]:
            if module.startswith(layer):
                module_layer = layer
                break

        if not module_layer:
            continue

        # Check each import
        for imp in imports:
            # Data access layer should not import from UI or backend
            if module_layer == "data_access" and imp in ["ui", "backend"]:
                violations.append(f"VIOLATION: {module} (data_access) imports {imp} (higher layer)")

            # Config should not import from any application layer
            if module_layer == "config" and imp in ["ui", "backend", "data_access"]:
                violations.append(f"VIOLATION: {module} (config) imports {imp} (application layer)")

            # Backend should not import from UI
            if module_layer == "backend" and imp == "ui":
                violations.append(f"VIOLATION: {module} (backend) imports {imp} (higher layer)")

    return violations


def generate_dependency_report(root_dir: Path) -> str:
    """Generate a comprehensive dependency report."""
    graph = build_dependency_graph(root_dir)
    cycles = detect_cycles(graph)
    violations = check_layer_violations(graph)
    layers = analyze_module_layers(graph)

    report = []
    report.append("=" * 80)
    report.append("NEXO SOLAR - CIRCULAR IMPORT ANALYSIS REPORT")
    report.append("=" * 80)
    report.append("")

    # Summary
    report.append("SUMMARY")
    report.append("-" * 80)
    report.append(f"Total modules analyzed: {len(graph)}")
    report.append(f"Circular dependencies found: {len(cycles)}")
    report.append(f"Layer violations found: {len(violations)}")
    report.append("")

    # Circular dependencies
    report.append("CIRCULAR DEPENDENCIES")
    report.append("-" * 80)
    if cycles:
        for i, cycle in enumerate(cycles, 1):
            report.append(f"\nCycle {i}:")
            report.append("  " + " -> ".join(cycle))
    else:
        report.append("✓ No circular dependencies detected!")
    report.append("")

    # Layer violations
    report.append("ARCHITECTURAL LAYER VIOLATIONS")
    report.append("-" * 80)
    if violations:
        for violation in violations:
            report.append(f"  {violation}")
    else:
        report.append("✓ No layer violations detected!")
    report.append("")

    # Module dependency graph
    report.append("MODULE DEPENDENCY GRAPH")
    report.append("-" * 80)
    for layer_name in ["config", "data_access", "backend", "ui", "migrations", "tests"]:
        layer_modules = [m for m in graph.keys() if m.startswith(layer_name)]
        if layer_modules:
            report.append(f"\n{layer_name.upper()} Layer:")
            for module in sorted(layer_modules):
                imports = graph.get(module, [])
                if imports:
                    report.append(f"  {module}")
                    for imp in sorted(set(imports)):
                        report.append(f"    -> {imp}")

    report.append("")
    report.append("=" * 80)

    return "\n".join(report)


def main():
    """Main entry point."""
    # Get the modbuspython directory
    script_dir = Path(__file__).parent.parent

    print("Analyzing imports in modbuspython package...")
    print(f"Root directory: {script_dir}")
    print()

    report = generate_dependency_report(script_dir)
    print(report)

    # Save report to file
    report_path = script_dir / "tests" / "circular_imports_report.txt"
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
