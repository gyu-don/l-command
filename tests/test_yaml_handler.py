"""
Tests for YAMLHandler.
"""

import tempfile
from pathlib import Path

from l_command.handlers.yaml import YAMLHandler


def test_can_handle_yaml_extensions() -> None:
    """Test YAML handler detection by extension."""
    extensions = [".yaml", ".yml"]

    for ext in extensions:
        with tempfile.NamedTemporaryFile(suffix=ext, mode="w") as tmp:
            tmp.write("key: value\nlist:\n  - item1\n  - item2")
            tmp.flush()
            path = Path(tmp.name)
            assert YAMLHandler.can_handle(path) is True, f"Failed for extension {ext}"

    # Non-YAML extension
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        path = Path(tmp.name)
        assert YAMLHandler.can_handle(path) is False


def test_can_handle_yaml_content() -> None:
    """Test YAML handler detection by content."""
    # YAML document separator
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w") as tmp:
        tmp.write("---\nkey: value\nother: data")
        tmp.flush()
        path = Path(tmp.name)
        assert YAMLHandler.can_handle(path) is True

    # YAML version directive
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w") as tmp:
        tmp.write("%YAML 1.2\n---\nkey: value")
        tmp.flush()
        path = Path(tmp.name)
        assert YAMLHandler.can_handle(path) is True

    # YAML-like structure
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w") as tmp:
        tmp.write("key1: value1\nkey2: value2\nlist:\n  - item1\n  - item2")
        tmp.flush()
        path = Path(tmp.name)
        assert YAMLHandler.can_handle(path) is True

    # Non-YAML content
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w") as tmp:
        tmp.write("This is just regular text")
        tmp.flush()
        path = Path(tmp.name)
        assert YAMLHandler.can_handle(path) is False


def test_priority() -> None:
    """Test YAML handler priority."""
    assert YAMLHandler.priority() == 30
