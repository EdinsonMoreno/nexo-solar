# Nexo Solar - Testing & Analysis Tools

This directory contains testing utilities and code analysis tools for the Nexo Solar project.

## Quick Start

### Check for Circular Imports

```bash
python -m modbuspython.tests.check_circular_imports
```

**Expected Output:**
```
✓ No circular dependencies detected!
✓ No layer violations detected!
```

## Available Tools

### 1. Circular Import Detector

**File:** `check_circular_imports.py`

**Purpose:** Automatically detect circular dependencies and architectural layer violations.

**Features:**
- AST-based import analysis
- Cycle detection using DFS algorithm
- Layer violation checking
- Dependency graph generation
- Automated report generation

**Usage:**
```bash
# Run from project root
python -m modbuspython.tests.check_circular_imports

# Output files:
# - Console: Summary report
# - File: modbuspython/tests/circular_imports_report.txt
```

**What it checks:**
- ✅ No circular imports between modules
- ✅ UI layer doesn't import from Data Access
- ✅ Backend layer doesn't import from UI
- ✅ Proper dependency flow (UI → Backend → Data Access)

## Documentation

### Generated Documentation Files

1. **`circular_imports_report.txt`**
   - Automated analysis report
   - Module dependency graph
   - Summary statistics

2. **`module_dependencies.md`**
   - Detailed architecture documentation
   - Dependency rules and guidelines
   - Communication patterns
   - Maintenance guidelines
   - Testing strategies

3. **`dependency_diagram.md`**
   - Visual Mermaid diagrams
   - Layer interaction flows
   - Signal-slot communication patterns
   - Module interaction matrix

## Architecture Rules

### Allowed Dependencies

```
UI Layer
  ↓ (can import)
Backend Layer
  ↓ (can import)
External Libraries
```

### Prohibited Dependencies

❌ Backend → UI
❌ Data Access → Backend
❌ Data Access → UI
❌ Any reverse dependencies

## Integration with Development Workflow

### Pre-commit Check

Add to your pre-commit hook:

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Checking for circular imports..."
python -m modbuspython.tests.check_circular_imports

if [ $? -ne 0 ]; then
    echo "❌ Circular imports detected! Commit aborted."
    exit 1
fi

echo "✅ No circular imports found."
```

### CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  check-imports:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - name: Check Circular Imports
        run: |
          python -m modbuspython.tests.check_circular_imports
```

## Troubleshooting

### Common Issues

**Issue:** Script fails to run
```bash
# Solution: Ensure you're in the project root
cd /path/to/nexo-solar
python -m modbuspython.tests.check_circular_imports
```

**Issue:** Import errors when running script
```bash
# Solution: Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

**Issue:** False positives in detection
```bash
# Solution: Check if __init__.py files are properly configured
# Ensure all packages have __init__.py files
```

## Maintenance

### When to Run

Run the circular import checker:
- ✅ Before committing code
- ✅ After adding new modules
- ✅ After refactoring imports
- ✅ During code review
- ✅ In CI/CD pipeline

### Updating the Tool

If you need to modify the detection logic:

1. Edit `check_circular_imports.py`
2. Test with known circular imports
3. Verify it catches violations
4. Update documentation

## Future Enhancements

Planned improvements:
- [ ] Add support for external dependency analysis
- [ ] Generate interactive HTML reports
- [ ] Add metrics for code complexity
- [ ] Integration with linting tools
- [ ] Automatic fix suggestions

## Related Documentation

- **Requirements:** `.kiro/specs/nexo-solar-production-refactoring/requirements.md`
- **Design:** `.kiro/specs/nexo-solar-production-refactoring/design.md`
- **Tasks:** `.kiro/specs/nexo-solar-production-refactoring/tasks.md`
- **Verification:** `.kiro/specs/nexo-solar-production-refactoring/circular_imports_verification.md`

## Contact

For questions or issues with the analysis tools, refer to the project documentation or create an issue in the repository.

---

**Last Updated:** 2025-01-XX
**Tool Version:** 1.0
**Status:** ✅ Production Ready
