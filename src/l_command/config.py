"""Configuration management for l-command."""

import logging
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class HandlerConfig:
    """Configuration for a single handler.

    Attributes:
        enabled: Whether the handler is enabled.
        priority: Priority of the handler (higher is evaluated first).
                  If None, use the handler's default priority.
        options: Handler-specific options (arbitrary key-value pairs).
    """

    enabled: bool = True
    priority: int | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneralConfig:
    """General configuration.

    Attributes:
        version: Configuration file schema version for future compatibility.
                 Format: "{major}.{minor}" (e.g., "1.0", "1.1", "2.0")
    """

    version: str = "1.0"


@dataclass
class Config:
    """Complete configuration for l-command.

    Attributes:
        general: General configuration.
        handlers: Dictionary mapping handler names to their configurations.
    """

    general: GeneralConfig = field(default_factory=GeneralConfig)
    handlers: dict[str, HandlerConfig] = field(default_factory=dict)

    @classmethod
    def default(cls: type["Config"]) -> "Config":
        """Return the default configuration.

        Returns:
            Default configuration with all handlers enabled at their default priorities.
        """
        return cls(
            general=GeneralConfig(),
            handlers={
                "directory": HandlerConfig(enabled=True, priority=100),
                "archive": HandlerConfig(enabled=True, priority=80),
                "image": HandlerConfig(enabled=True, priority=65),
                "pdf": HandlerConfig(enabled=True, priority=60),
                "binary": HandlerConfig(enabled=True, priority=60),
                "media": HandlerConfig(enabled=True, priority=55),
                "json": HandlerConfig(enabled=True, priority=50),
                "xml": HandlerConfig(enabled=True, priority=45),
                "csv": HandlerConfig(enabled=True, priority=40),
                "markdown": HandlerConfig(enabled=True, priority=35),
                "yaml": HandlerConfig(enabled=True, priority=30),
                "default": HandlerConfig(enabled=True, priority=0),
            },
        )


def find_config_file() -> Path | None:
    """Find the configuration file in standard locations.

    Search order:
    1. $XDG_CONFIG_HOME/l-command/config.toml
    2. ~/.config/l-command/config.toml
    3. ~/.l-command/config.toml
    4. ./l-command.toml (current directory)

    Returns:
        Path to the configuration file if found, None otherwise.
    """
    search_paths = []

    # 1. XDG_CONFIG_HOME
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        search_paths.append(Path(xdg_config_home) / "l-command" / "config.toml")

    # 2. ~/.config/l-command/config.toml
    home = Path.home()
    search_paths.append(home / ".config" / "l-command" / "config.toml")

    # 3. ~/.l-command/config.toml
    search_paths.append(home / ".l-command" / "config.toml")

    # 4. ./l-command.toml
    search_paths.append(Path.cwd() / "l-command.toml")

    for path in search_paths:
        if path.exists() and path.is_file():
            return path

    return None


def parse_toml_file(path: Path) -> dict:
    """Parse a TOML file.

    Args:
        path: Path to the TOML file.

    Returns:
        Parsed TOML data as a dictionary.

    Raises:
        ValueError: If the file cannot be parsed.
    """
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ValueError(f"Failed to parse TOML file {path}: {e}") from e
    except OSError as e:
        raise ValueError(f"Failed to read file {path}: {e}") from e


def validate_handler_config(name: str, data: dict) -> HandlerConfig | None:
    """Validate and convert handler configuration data.

    Args:
        name: Handler name.
        data: Raw configuration data.

    Returns:
        HandlerConfig object if valid, None if invalid.
    """
    if not isinstance(data, dict):
        logger.warning(f"Invalid handler config for '{name}': expected dict, got {type(data)}")
        return None

    enabled = data.get("enabled", True)
    if not isinstance(enabled, bool):
        logger.warning(f"Invalid 'enabled' value for handler '{name}': expected bool, got {type(enabled)}")
        enabled = True

    priority = data.get("priority")
    if priority is not None and not isinstance(priority, int):
        logger.warning(f"Invalid 'priority' value for handler '{name}': expected int, got {type(priority)}")
        priority = None

    # Parse handler-specific options
    options = data.get("options", {})
    if not isinstance(options, dict):
        logger.warning(f"Invalid 'options' value for handler '{name}': expected dict, got {type(options)}")
        options = {}

    return HandlerConfig(enabled=enabled, priority=priority, options=options)


def load_config_from_dict(data: dict) -> Config:
    """Load configuration from parsed TOML data.

    Args:
        data: Parsed TOML data.

    Returns:
        Config object with merged settings.
    """
    config = Config.default()

    # Parse general section
    if "general" in data and isinstance(data["general"], dict):
        general_data = data["general"]
        if "version" in general_data and isinstance(general_data["version"], str):
            config.general.version = general_data["version"]

    # Parse handlers section
    if "handlers" in data and isinstance(data["handlers"], dict):
        handlers_data = data["handlers"]
        for name, handler_data in handlers_data.items():
            handler_config = validate_handler_config(name, handler_data)
            if handler_config is not None:
                # Merge with default config
                if name in config.handlers:
                    default_config = config.handlers[name]
                    # Override only specified values
                    if handler_config.priority is None:
                        handler_config.priority = default_config.priority
                    config.handlers[name] = handler_config
                else:
                    logger.warning(f"Unknown handler '{name}' in configuration file")

    return config


def load_config(path: Path | None = None) -> Config:
    """Load configuration from file or return default.

    Args:
        path: Path to configuration file. If None, search standard locations.

    Returns:
        Loaded configuration or default if no file found.
    """
    if path is None:
        path = find_config_file()

    if path is None:
        logger.debug("No configuration file found, using defaults")
        return Config.default()

    try:
        logger.debug(f"Loading configuration from {path}")
        data = parse_toml_file(path)
        return load_config_from_dict(data)
    except ValueError as e:
        logger.warning(f"Failed to load configuration: {e}. Using defaults.")
        return Config.default()
