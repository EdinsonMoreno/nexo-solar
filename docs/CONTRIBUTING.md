> Flujo vigente: [dev → QA → main](WORKFLOW.md). Esta guía técnica conserva detalles de la base inicial.

# Contributing Guide

## Welcome

Thank you for your interest in contributing to Nexo Solar. This guide covers development workflow, coding standards, testing, and submission process.

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/EdinsonMoreno/nexo-solar.git
cd nexo-solar
```

### 2. Create Virtual Environment

```bash
# Python 3.10+ required
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Install Pre-commit Hooks

```bash
pre-commit install
```

### 5. Configure Environment

```bash
cp .env.example .env
cp config.example.yaml config.yaml
# Edit .env and config.yaml with your settings
```

## Code Organization

### Directory Structure

```
modbuspython/
├── ui/                 # Presentation layer (PyQt6)
├── backend/            # Business logic
├── data_access/        # Data access & I/O
├── config/             # Configuration management
├── migrations/         # Database migrations
└── tests/              # Test suites
```

### Layer Responsibilities

| Layer | Location | Responsibility |
|-------|----------|---------------|
| Presentation | `ui/` | UI components, signals/slots, user interaction |
| Business Logic | `backend/` | Domain rules, calculations, state management |
| Data Access | `data_access/` | I/O operations, database, network, logging |
| Configuration | `config/` | Config loading, validation, encryption |

### Layer Dependency Rules

```
ui → backend → data_access → config
```

- **Never** import UI in backend or data_access
- **Never** import backend in data_access
- **Never** hardcode configuration values; use ConfigurationManager
- **Always** use Repository pattern for database access

## Coding Standards

### Python Style

- **Formatter:** Black (120 line length)
- **Linter:** Flake8
- **Type Checking:** Mypy (strict mode)
- **Import Sorting:** Isort

### File Constraints

- **Maximum file size:** 500 lines
- If a file exceeds 500 lines, refactor by extracting responsibilities
- Use descriptive module names

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Modules | snake_case | `modbus_client.py` |
| Classes | PascalCase | `ModbusClient` |
| Functions | snake_case | `read_irradiance()` |
| Constants | UPPER_SNAKE | `MAX_RETRIES` |
| Private members | Leading underscore | `_internal_method()` |

### Type Hints

All functions must have type hints:

```python
def read_irradiance(client: ModbusTcpClient, register: int) -> float:
    """Read irradiance from Modbus register."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_hra(lat: float, lon: float) -> float:
    """Calculate Hour Angle from sunrise.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        Hour angle in degrees.

    Raises:
        ValueError: If latitude is outside [-90, 90].
    """
```

## Testing

### Test Organization

```
tests/
├── unit/               # Isolated component tests
├── integration/        # Cross-component tests
└── property_based/     # Hypothesis property tests
```

### Running Tests

```bash
# All tests
python -m pytest

# Unit tests only
python -m pytest tests/unit/

# With coverage
python -m pytest --cov=modbuspython --cov-report=html

# Property-based tests only
python -m pytest tests/property_based/
```

### Writing Tests

#### Unit Tests

```python
def test_read_irradiance_success(mock_client: Mock):
    """Test successful irradiance reading."""
    mock_client.read_input_registers.return_value = [1234]
    reader = ModbusReader(mock_client, IrradianceRepository())
    result = reader.read_irradiance(4)
    assert result == 12.34
```

#### Property-Based Tests

```python
@given(st.floats(min_value=-90, max_value=90))
def test_declination_range(lat: float):
    """Declination must always be between -23.45 and 23.45."""
    decl = solar_calcs.calculate_decl(lat)
    assert -23.45 <= decl <= 23.45
```

### Test Requirements

- **Minimum coverage:** 80%
- **No skipped tests** without justification
- **Mock external I/O** (network, database, file system)
- **Use fixtures** for common setup

## Pre-commit Hooks

18 hooks run automatically on commit:

| Category | Hooks |
|----------|-------|
| Formatting | black, isort, trailing-whitespace, end-of-file-fixer |
| Linting | flake8, pylint, bandit, security-check |
| Types | mypy, pyright |
| Checks | check-yaml, check-json, check-toml, check-added-large-files |
| Quality | radon (complexity), xenon (maintenance) |

### Running Hooks Manually

```bash
# Run all hooks
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
```

## Commits

### Message Format

```
type(scope): description

[optional body]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

### Examples

```
feat(ui): add 3D viewer for solar tracker
fix(modbus): handle connection timeout gracefully
docs(config): update environment variable examples
refactor(data_access): split database manager into repositories
```

## Pull Requests

### Before Submitting

1. Run tests: `python -m pytest`
2. Run linters: `pre-commit run --all-files`
3. Update documentation if needed
4. Synchronize with dev before submitting development changes

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests passing

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
```

### Review Process

1. Automated checks must pass (CI/CD)
2. At least 1 code review approval required
3. All conversations resolved
4. Promote dev to QA for validation, then QA to main after approval

## Database Migrations

### Creating a Migration

```python
# modbuspython/migrations/versions/002_add_sensor_table.py

def upgrade(db):
    db.execute("""
        CREATE TABLE sensors (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)

def downgrade(db):
    db.execute("DROP TABLE sensors")
```

### Running Migrations

```python
from modbuspython.migrations.migration_manager import MigrationManager

manager = MigrationManager()
manager.run_migrations()
```

## Debugging

### Logging

```python
from modbuspython.data_access.logging_service import LoggingService

logger = LoggingService().get_logger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### Interactive Debugging

```bash
# Run with debugger
python -m pdb run.py

# Or use IDE debugger (VS Code, PyCharm)
```

## Release Process

1. Update version in `pyproject.toml`
2. Create release branch: `git checkout -b release/v1.2.0`
3. Update CHANGELOG.md
4. Run full test suite
5. Tag release: `git tag v1.2.0`
6. Push tag: `git push origin v1.2.0`
7. Create GitHub Release

## Getting Help

- **Documentation:** `docs/` directory
- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions
