"""Tests for configuration management."""

from pathlib import Path

import pytest

from l_command.config import (
    Config,
    GeneralConfig,
    HandlerConfig,
    find_config_file,
    load_config,
    load_config_from_dict,
    parse_toml_file,
    validate_handler_config,
)


def test_handler_config_defaults() -> None:
    """Test HandlerConfig default values."""
    config = HandlerConfig()
    assert config.enabled is True
    assert config.priority is None
    assert config.options == {}


def test_handler_config_with_options() -> None:
    """Test HandlerConfig with custom options."""
    config = HandlerConfig(enabled=False, priority=100, options={"key": "value", "count": 42})
    assert config.enabled is False
    assert config.priority == 100
    assert config.options == {"key": "value", "count": 42}


def test_general_config_defaults() -> None:
    """Test GeneralConfig default values."""
    config = GeneralConfig()
    assert config.version == "1.0"


def test_config_default() -> None:
    """Test Config.default() creates proper default configuration."""
    config = Config.default()
    assert config.general.version == "1.0"
    assert len(config.handlers) == 12

    # Check some specific handlers
    assert config.handlers["json"].enabled is True
    assert config.handlers["json"].priority == 50
    assert config.handlers["json"].options == {}

    assert config.handlers["directory"].enabled is True
    assert config.handlers["directory"].priority == 100

    assert config.handlers["default"].enabled is True
    assert config.handlers["default"].priority == 0


def test_find_config_file_not_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test find_config_file when no config file exists."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.chdir(tmp_path)

    assert find_config_file() is None


def test_find_config_file_in_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test find_config_file in ~/.config/l-command/."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.chdir(tmp_path)

    config_dir = tmp_path / ".config" / "l-command"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    config_file.write_text('[general]\nversion = "1.0"\n')

    found = find_config_file()
    assert found == config_file


def test_find_config_file_in_xdg_config_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test find_config_file with XDG_CONFIG_HOME."""
    xdg_config = tmp_path / "xdg_config"
    xdg_config.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config))
    monkeypatch.chdir(tmp_path)

    config_dir = xdg_config / "l-command"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text('[general]\nversion = "1.0"\n')

    found = find_config_file()
    assert found == config_file


def test_find_config_file_in_home_dot_l_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test find_config_file in ~/.l-command/."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.chdir(tmp_path)

    config_dir = tmp_path / ".l-command"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text('[general]\nversion = "1.0"\n')

    found = find_config_file()
    assert found == config_file


def test_find_config_file_in_current_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test find_config_file in current directory."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.chdir(tmp_path)

    config_file = tmp_path / "l-command.toml"
    config_file.write_text('[general]\nversion = "1.0"\n')

    found = find_config_file()
    assert found == config_file


def test_parse_toml_file_valid(tmp_path: Path) -> None:
    """Test parse_toml_file with valid TOML."""
    config_file = tmp_path / "config.toml"
    config_file.write_text('[general]\nversion = "1.0"\n')

    data = parse_toml_file(config_file)
    assert data == {"general": {"version": "1.0"}}


def test_parse_toml_file_invalid(tmp_path: Path) -> None:
    """Test parse_toml_file with invalid TOML."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("invalid toml [[[")

    with pytest.raises(ValueError, match="Failed to parse TOML file"):
        parse_toml_file(config_file)


def test_parse_toml_file_not_found(tmp_path: Path) -> None:
    """Test parse_toml_file with non-existent file."""
    config_file = tmp_path / "nonexistent.toml"

    with pytest.raises(ValueError, match="Failed to read file"):
        parse_toml_file(config_file)


def test_validate_handler_config_valid() -> None:
    """Test validate_handler_config with valid data."""
    data = {"enabled": True, "priority": 50, "options": {"key": "value"}}
    config = validate_handler_config("json", data)

    assert config is not None
    assert config.enabled is True
    assert config.priority == 50
    assert config.options == {"key": "value"}


def test_validate_handler_config_partial() -> None:
    """Test validate_handler_config with partial data."""
    data = {"priority": 70}
    config = validate_handler_config("json", data)

    assert config is not None
    assert config.enabled is True  # default
    assert config.priority == 70
    assert config.options == {}  # default


def test_validate_handler_config_invalid_type() -> None:
    """Test validate_handler_config with invalid type."""
    config = validate_handler_config("json", "not a dict")  # type: ignore
    assert config is None


def test_validate_handler_config_invalid_enabled() -> None:
    """Test validate_handler_config with invalid enabled value."""
    data = {"enabled": "yes"}
    config = validate_handler_config("json", data)

    assert config is not None
    assert config.enabled is True  # falls back to default


def test_validate_handler_config_invalid_priority() -> None:
    """Test validate_handler_config with invalid priority value."""
    data = {"priority": "high"}
    config = validate_handler_config("json", data)

    assert config is not None
    assert config.priority is None  # falls back to None


def test_validate_handler_config_invalid_options() -> None:
    """Test validate_handler_config with invalid options value."""
    data = {"options": "not a dict"}
    config = validate_handler_config("json", data)

    assert config is not None
    assert config.options == {}  # falls back to empty dict


def test_load_config_from_dict_empty() -> None:
    """Test load_config_from_dict with empty dict."""
    config = load_config_from_dict({})
    assert config.general.version == "1.0"
    assert len(config.handlers) == 12


def test_load_config_from_dict_with_general() -> None:
    """Test load_config_from_dict with general section."""
    data = {"general": {"version": "2.0"}}
    config = load_config_from_dict(data)
    assert config.general.version == "2.0"


def test_load_config_from_dict_with_handlers() -> None:
    """Test load_config_from_dict with handlers section."""
    data = {
        "handlers": {
            "json": {"enabled": False, "priority": 70},
            "pdf": {"priority": 100},
        }
    }
    config = load_config_from_dict(data)

    assert config.handlers["json"].enabled is False
    assert config.handlers["json"].priority == 70

    assert config.handlers["pdf"].enabled is True
    assert config.handlers["pdf"].priority == 100


def test_load_config_from_dict_with_options() -> None:
    """Test load_config_from_dict with handler options."""
    data = {
        "handlers": {
            "json": {
                "enabled": True,
                "priority": 50,
                "options": {"jq_args": ["--indent", "2"], "max_size_mb": 20},
            }
        }
    }
    config = load_config_from_dict(data)

    assert config.handlers["json"].options == {
        "jq_args": ["--indent", "2"],
        "max_size_mb": 20,
    }


def test_load_config_from_dict_unknown_handler() -> None:
    """Test load_config_from_dict with unknown handler (should warn)."""
    data = {"handlers": {"unknown": {"enabled": True}}}
    config = load_config_from_dict(data)

    # Unknown handler should not be added
    assert "unknown" not in config.handlers


def test_load_config_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test load_config when no config file exists."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.chdir(tmp_path)

    config = load_config()
    assert config.general.version == "1.0"
    assert len(config.handlers) == 12


def test_load_config_with_file(tmp_path: Path) -> None:
    """Test load_config with a config file."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[general]
version = "1.1"

[handlers.json]
enabled = false
priority = 70

[handlers.json.options]
jq_args = ["--indent", "2"]
max_size_mb = 20

[handlers.pdf]
priority = 100
"""
    )

    config = load_config(config_file)
    assert config.general.version == "1.1"
    assert config.handlers["json"].enabled is False
    assert config.handlers["json"].priority == 70
    assert config.handlers["json"].options == {
        "jq_args": ["--indent", "2"],
        "max_size_mb": 20,
    }
    assert config.handlers["pdf"].enabled is True
    assert config.handlers["pdf"].priority == 100
    assert config.handlers["pdf"].options == {}


def test_load_config_with_invalid_file(tmp_path: Path) -> None:
    """Test load_config with invalid TOML file (should fall back to defaults)."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("invalid toml [[[")

    config = load_config(config_file)
    # Should fall back to defaults
    assert config.general.version == "1.0"
    assert len(config.handlers) == 12
