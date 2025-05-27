# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Important**: Use `uv run` prefix for all Python commands.

- **Test**: `uv run pytest tests/`
- **Test with coverage**: `uv run pytest --cov=src/l_command tests/`
- **Lint**: `uv run ruff check .`
- **Auto-fix linting**: `uv run ruff check --fix .`
- **Format**: `uv run ruff format .`
- **Run single test**: `uv run pytest tests/test_<specific_test>.py`
- **Pre-commit**: `uv run pre-commit run --all-files`
- **Add package**: `uv add <package-name>` (use `uv add --dev <package-name>` for dev dependencies)

## Architecture Overview

This is a Python CLI tool (`l`) that intelligently displays files and directories using a handler-based architecture.

### Core Architecture

The application uses a **chain-of-responsibility pattern** with file handlers:

1. **Entry Point**: `src/l_command/cli.py:main()` - parses args and delegates to handlers
2. **Handler Registry**: `src/l_command/handlers/__init__.py:get_handlers()` - returns handlers in priority order
3. **Handler Chain**: Each handler implements `FileHandler` base class with:
   - `can_handle(path)` - determines if handler processes this path type
   - `handle(path)` - processes the path
   - `priority()` - determines evaluation order (higher first)

### Handler Priority Order

1. `DirectoryHandler` - processes directories (runs `ls -la --color=auto`)
2. `JsonHandler` - detects and formats JSON files using `jq`
3. `ArchiveHandler` - lists contents of archives (zip, tar variants)
4. `BinaryHandler` - displays binary files using `hexdump -C`
5. `DefaultFileHandler` - handles text files (cat for short, less for long)

### Key Behaviors

- **JSON Detection**: Files with `.json` extension OR files starting with `{`/`[` (with UTF-8 validation)
- **Archive Detection**: Supports ZIP, TAR variants (.tar.gz, .tgz, .tar.bz2, etc.)
- **Binary Detection**: Uses `file` command when available, falls back to null-byte detection
- **Smart Paging**: Uses terminal height to decide between `cat` and `less -RFX`

### Project Structure

- `src/l_command/` - main package
  - `cli.py` - entry point and argument parsing
  - `constants.py` - shared constants
  - `utils.py` - utility functions
  - `handlers/` - file type handlers
- `tests/` - pytest test suite with test files in `test_files/`

### Execution Flow

1. User executes `l [path]`
2. Check if path exists
3. Iterate through handlers in priority order
4. First handler that returns `True` for `can_handle(path)` processes the path
5. If no handler can handle the path, display an error message

## Adding New Handlers

### How to Add a New File Type Handler

To add support for a new file type (e.g., YAML, Markdown), follow these steps:

1. **Create a new handler class** that inherits from `FileHandler`:

```python
from l_command.handlers.base import FileHandler

class YamlHandler(FileHandler):
    """Handler for YAML files."""

    @classmethod
    def can_handle(cls, path: Path) -> bool:
        """Determine if this handler can process the path."""
        if not path.is_file():
            return False

        # Extension-based detection
        if path.suffix.lower() in [".yml", ".yaml"]:
            return True

        # Content-based detection (optional)
        try:
            with path.open("rb") as f:
                content_start = f.read(1024)
                # YAML detection logic
        except OSError:
            pass

        return False

    @classmethod
    def handle(cls, path: Path) -> None:
        """Process the YAML file."""
        # Size check
        # Tool existence check
        # Display processing

    @classmethod
    def priority(cls) -> int:
        """Return the priority of this handler."""
        return 70  # Between JSON (50) and Archive (80)
```

2. **Register the handler** in `handlers/__init__.py`:

```python
from l_command.handlers.yaml import YamlHandler

def get_handlers() -> list[type[FileHandler]]:
    """Return all available handlers in priority order."""
    handlers: list[type[FileHandler]] = [
        DirectoryHandler,
        JsonHandler,
        YamlHandler,  # Add the new handler here
        ArchiveHandler,
        BinaryHandler,
        DefaultFileHandler,
    ]
    return sorted(handlers, key=lambda h: h.priority(), reverse=True)
```

### Implementation Best Practices

1. **Single Responsibility Principle**: Each function has one responsibility
   - Example: `JsonHandler.can_handle()` only determines if a file is JSON

2. **Graceful Failure**: Implement appropriate error handling
   - Fallback when tools don't exist
   - Handle file access errors

3. **Centralized Configuration**: Constants are centralized in `constants.py`

4. **Command Execution Optimization**:
   - Avoid unnecessary process creation
   - Be careful with large file processing (memory usage)
   - Prioritize user experience (processing speed, visual consistency)

## Testing Strategy

### Types of Tests

1. **Unit Tests**: Test individual functions
   - Handler detection methods
   - Utility functions

2. **Integration Tests**: Test overall command behavior
   - Behavior of `main()` with various inputs
   - Accuracy of subprocess calls

3. **Mock Tests**: Test with mocked external dependencies
   - Mock `subprocess` module
   - Mock filesystem operations

### Test Examples

**JSON file detection test:**

```python
def test_json_handler_can_handle_with_json_extension():
    # Test detection of files with .json extension
    temp_file = Path("test.json")
    assert JsonHandler.can_handle(temp_file) == True

def test_json_handler_can_handle_with_json_content():
    # Test detection of files with JSON content but no .json extension
    temp_file = Path("test_no_ext")
    # Create test file with JSON content
    with temp_file.open("w") as f:
        f.write('{"key": "value"}')
    try:
        assert JsonHandler.can_handle(temp_file) == True
    finally:
        # Clean up test file
        temp_file.unlink()
```

**Subprocess call test:**

```python
@patch("subprocess.run")
def test_default_file_handler_short_file(mock_run):
    # Test that cat is used for files shorter than terminal height
    # Set up test file and mock
    # Call DefaultFileHandler.handle()
    # Verify subprocess.run was called with cat
    mock_run.assert_called_once_with(["cat", ANY], check=True)
```

## FAQ

### Q: How do I run a specific test?

A: Use pytest with the specific test path:
```bash
uv run pytest tests/test_json_detection.py::test_json_handler_can_handle
```

### Q: How can I efficiently process large files?

A: Consider these strategies:
- Stream processing (don't load the entire file into memory)
- Sampling (only display the first part of large files)
- Appropriate paging (`less`)
- Appropriate timeout handling

## Development Guidelines

### Coding Standards
- Code, comments, docstrings MUST be written in English
- Use `pathlib` instead of `os.path`
- Follow RFC 2119 keywords: MUST, SHOULD, etc.
- Code style enforced by ruff (line length 120, Google docstring convention)
- Type hints are required
- Functions and classes must have docstrings (Google style)

### Git Workflow
- Commit messages MUST follow Conventional Commit 1.0.0 format and be written in English
- タスクはこまめに区切ります。多くのことを行っていると感じたら、一度コミットしてタスクを区切ることを提案してください

### Pre-commit Process
1. Stage files: `git add <file-name> ...`
2. Run pre-commit: `uv run pre-commit run`
3. If failed, check output and re-add modified files
4. Repeat until pre-commit passes
5. Then commit

### Useful Tips
- For git commands with pagers, use `| cat` to avoid `less` viewer
- Repository URL: https://github.com/gyu-don/l-command
