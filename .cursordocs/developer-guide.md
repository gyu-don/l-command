# Developer Guide

This document provides detailed information for developers working on the `l` command.

## Project Architecture

### Overall Structure

The `l` command consists of the following main components:

- **CLI Interface** (`cli.py`): Entry point for parsing command line arguments and processing
- **Constants Module** (`constants.py`): Definition of configuration values and constants
- **Utilities** (`utils.py`): Common utility functions
- **Handlers**: A modular system for processing different file types and directories

### Handler Architecture

The project uses a handler-based architecture where each handler:
1. Implements `can_handle()` to determine if it can process a given path
2. Implements `handle()` to actually process the path
3. Can specify a priority to determine the order in which handlers are evaluated

Current handlers include:
- `DirectoryHandler`: For directories (highest priority)
- `JsonHandler`: For JSON files
- `ArchiveHandler`: For archive files (ZIP, TAR, etc.)
- `BinaryHandler`: For binary files
- `DefaultFileHandler`: For regular text files (lowest priority)

### Execution Flow

1. User executes `l [path]`
2. Check if path exists
3. Iterate through handlers in priority order
4. First handler that returns `True` for `can_handle(path)` processes the path
5. If no handler can handle the path, display an error message

## Implementation Status and Extension Methods

### Currently Implemented Features

- Directory display (`ls -la --color=auto`)
- File display (using `cat` or `less` based on file length)
- JSON file detection and formatting
  - Extension-based detection (`.json`)
  - Content-based detection (string starting with `{` or `[`)
  - Formatting with `jq`
  - Syntax checking and fallback for large files
- Archive file handling
  - ZIP files (including .jar, .war, .ear, .apk, .ipa)
  - TAR archives (including .tar.gz, .tgz, .tar.bz2, .tbz2, .tar.xz, .txz, .tar.zst)
- Binary file handling
  - Detection using `file` command or content analysis
  - Display using `hexdump -C`

### How to Add a New Handler

To add support for a new file type (e.g., YAML, Markdown), follow these steps:

1. Create a new handler class that inherits from `FileHandler`:
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

2. Register the handler in `handlers/__init__.py`:
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

JSON file detection test example:

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

Subprocess call test example:

```python
@patch("subprocess.run")
def test_default_file_handler_short_file(mock_run):
    # Test that cat is used for files shorter than terminal height
    # Set up test file and mock
    # Call DefaultFileHandler.handle()
    # Verify subprocess.run was called with cat
    mock_run.assert_called_once_with(["cat", ANY], check=True)
```

## Best Practices

### Code Design

1. **Single Responsibility Principle**: Each function has one responsibility
   - Example: `JsonHandler.can_handle()` only determines if a file is JSON

2. **Graceful Failure**: Implement appropriate error handling
   - Fallback when tools don't exist
   - Handle file access errors

3. **Centralized Configuration**: Constants are centralized in `constants.py`

### Implementation Tips

1. **Adding New Features**:
   - Document the behavior specification first
   - Create test cases first (TDD)
   - Verify existing tests still pass after implementation

2. **Command Execution Optimization**:
   - Avoid unnecessary process creation
   - Be careful with large file processing (memory usage)
   - Prioritize user experience (processing speed, visual consistency)

## Frequently Asked Questions

### Q: How do I add support for a new file type?

A: See the "How to Add a New Handler" section. Basically, you need to:
1. Create a new handler class that inherits from `FileHandler`
2. Implement `can_handle()`, `handle()`, and `priority()` methods
3. Register the handler in `handlers/__init__.py`

### Q: How do I run tests?

A: Run tests with the following command:
```bash
uv run pytest tests/
```

To run a specific test:
```bash
uv run pytest tests/test_json_detection.py::test_json_handler_can_handle
```

### Q: How can I efficiently process large files?

A: Consider these strategies:
- Stream processing (don't load the entire file into memory)
- Sampling (only display the first part of large files)
- Appropriate paging (`less`)
- Appropriate timeout handling
