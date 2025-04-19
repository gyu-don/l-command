# Development Guidelines

## Language Requirements
- Product code and user-facing documentation: English
- Design documents: Japanese/English/Mixed allowed

## Environment Setup

### Required Tools
- Python 3.11 or higher
- uv (Python package manager)
- Git

### Development Environment Setup
```bash
# Clone the repository
git clone https://github.com/your-username/l-command.git
cd l-command

# Install uv (if you don't have it already)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

### Development Commands
```bash
# Run tests
uv run pytest tests/

# Run tests with coverage
uv run pytest --cov=src/l_command tests/

# Lint check
uv run ruff check .

# Code formatting
uv run ruff format .

# Run pre-commit hooks manually (all files)
uv run pre-commit run --all-files
```

### Using pre-commit
pre-commit hooks run automatically at these times:
- When committing
- When pushing (optional)

To run manually:
```bash
# Run on all files
uv run pre-commit run --all-files

# Run on specific files
uv run pre-commit run --files <filename>
```

pre-commit hooks perform the following checks:
- Code formatting and linting with ruff
- Large file checks
- Case conflict checks
- JSON/YAML file syntax checks
- Trailing whitespace checks

## Coding Standards

### Code Style
- Use ruff as formatter and linter
- Type hints are required
- Functions and classes must have docstrings (Google style recommended)

### ruff Configuration
The project already includes ruff configuration in `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py312"
line-length = 120
select = ["E", "F", "I", "N", "UP", "ANN", "B", "A", "C4", "SIM", "TD"]
ignore = []

[tool.ruff.lint.isort]
known-first-party = ["l_command"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"

[tool.ruff.lint.pydocstyle]
convention = "google"
```

### Type Hints Example
```python
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Tuple

def analyze_path(path: Optional[Path]) -> int:
    """
    Analyze a path and display it with the appropriate command.

    Args:
        path: Path to display. If None, process stdin.

    Returns:
        Exit code
    """
    # Implementation
```

## Git Commit Message Rules

### Basic Structure
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes only
- `style`: Changes that don't affect code meaning (whitespace, formatting, etc.)
- `refactor`: Code changes that are neither bug fixes nor feature additions
- `test`: Adding missing tests or fixing existing tests
- `chore`: Changes to build process or auxiliary tools

### Rules
1. Subject line should be 50 characters or less
2. Don't capitalize the subject line
3. Use imperative mood in the subject line
4. Don't end the subject line with a period
5. Wrap body text at 72 characters
6. Explain "what" and "why" in the body (not "how")

### Example
```
feat(cli): add version flag support

Add -v and --version flags to display the current version of the tool.
This resolves the user feedback issue #42.
```

## Quality Assurance

### Testing
- Create unit and integration tests using pytest
- Aim for 80% or higher test coverage

### GitHub CI Configuration
`.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install uv
      run: curl -LsSf https://astral.sh/uv/install.sh | sh

    - name: Install dependencies
      run: |
        uv pip install -e ".[dev]"

    - name: Lint with ruff
      run: ruff check .

    - name: Format check with ruff
      run: ruff format --check .

    - name: Test with pytest
      run: pytest
```

## Development Workflow

1. Create a branch for new features or bug fixes
2. Implement changes (including type hints)
3. Add and run tests
4. Format code: `ruff format .`
5. Run lint: `ruff check .`
6. Create a PR

## Project Structure
```
l-command/
├── README.md
├── LICENSE
├── CONTRIBUTING.md           # This development guide
├── pyproject.toml            # Project metadata, build settings
├── src/
│   └── l_command/
│       ├── __init__.py
│       ├── cli.py            # CLI entry point
│       ├── constants.py      # Constants
│       ├── utils.py          # Utility functions
│       └── handlers/         # File type handlers
│           ├── __init__.py
│           ├── base.py       # Base handler class
│           ├── default.py    # Default file handler
│           ├── directory.py  # Directory handler
│           ├── json.py       # JSON handler
│           ├── archive.py    # Archive handler
│           └── binary.py     # Binary handler
├── tests/                    # Tests
└── .cursordocs/              # Project documentation
```

## Dependency Management

This project uses `uv` for dependency management.

```bash
uv sync
```

## Packaging

```bash
# Build
uv pip install build
python -m build
```
