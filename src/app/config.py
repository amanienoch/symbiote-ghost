"""Validated, immutable configuration and local storage paths."""

from __future__ import annotations

import math
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


MAX_CONFIG_BYTES = 64 * 1024


class ConfigError(ValueError):
    """A configuration cannot be read, written, or validated."""


@dataclass(frozen=True)
class AIConfig:
    provider: str = "ollama"
    general_model: str = ""
    coding_model: str = ""
    vision_model: str = ""


@dataclass(frozen=True)
class ScreenConfig:
    capture_interval: float = 2.0
    change_threshold: float = 0.08


@dataclass(frozen=True)
class GhostConfig:
    enabled: bool = False


@dataclass(frozen=True)
class OCRConfig:
    enabled: bool = True


@dataclass(frozen=True)
class VoiceConfig:
    enabled: bool = False


@dataclass(frozen=True)
class PrivacyConfig:
    save_screenshots: bool = False


@dataclass(frozen=True)
class AppConfig:
    ai: AIConfig = field(default_factory=AIConfig)
    screen: ScreenConfig = field(default_factory=ScreenConfig)
    ghost: GhostConfig = field(default_factory=GhostConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)


class StrictSafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate and non-string keys."""

    def construct_mapping(
        self,
        node: yaml.MappingNode,
        deep: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(node, yaml.MappingNode):
            raise ConfigError("Configuration mappings are malformed.")

        result: dict[str, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ConfigError("Configuration keys must be strings.")
            if key in result:
                raise ConfigError("Configuration contains a duplicate key.")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def runtime_directory() -> Path:
    """Return per-user storage without depending on the working directory."""
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = (
            Path(local_app_data)
            if local_app_data
            else Path.home() / "AppData" / "Local"
        )
        return base / "SYMBIOTE-GHOST"

    # Useful for non-Windows development; Windows remains the target.
    state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(state_home) if state_home else Path.home() / ".local" / "state"
    return base / "symbiote-ghost"


def config_to_yaml(config: AppConfig) -> str:
    """Serialize supported configuration fields in a stable order."""
    return yaml.safe_dump(
        asdict(config),
        sort_keys=False,
        allow_unicode=True,
    )


def _boolean(value: Any, field_name: str) -> bool:
    if type(value) is not bool:
        raise ConfigError(f"{field_name} must be true or false.")
    return value


def _number(
    value: Any,
    field_name: str,
    minimum: float,
    maximum: float,
) -> float:
    if type(value) not in (int, float):
        raise ConfigError(f"{field_name} must be a number.")

    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ConfigError(f"{field_name} must be a finite number.") from exc

    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ConfigError(
            f"{field_name} must be between {minimum} and {maximum}."
        )
    return number


def _model_name(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{field_name} must be a string.")
    if len(value) > 256 or any(ord(character) < 32 for character in value):
        raise ConfigError(
            f"{field_name} must contain at most 256 characters "
            "and no control characters."
        )
    return value.strip()


def parse_config(document: Any) -> AppConfig:
    """Validate YAML data, applying defaults only to omitted fields."""
    if not isinstance(document, dict):
        raise ConfigError("Configuration must be a YAML mapping.")

    defaults = asdict(AppConfig())
    if any(key not in defaults for key in document):
        raise ConfigError("Configuration contains an unsupported section.")

    sections: dict[str, dict[str, Any]] = {}
    for section_name, section_defaults in defaults.items():
        supplied = document.get(section_name, {})
        if not isinstance(supplied, dict):
            raise ConfigError(f"{section_name} must be a mapping.")
        if any(key not in section_defaults for key in supplied):
            raise ConfigError(
                f"{section_name} contains an unsupported setting."
            )
        sections[section_name] = {**section_defaults, **supplied}

    ai = sections["ai"]
    screen = sections["screen"]
    if ai["provider"] != "ollama":
        raise ConfigError("ai.provider must be ollama.")

    return AppConfig(
        ai=AIConfig(
            provider="ollama",
            general_model=_model_name(ai["general_model"], "ai.general_model"),
            coding_model=_model_name(ai["coding_model"], "ai.coding_model"),
            vision_model=_model_name(ai["vision_model"], "ai.vision_model"),
        ),
        screen=ScreenConfig(
            capture_interval=_number(
                screen["capture_interval"],
                "screen.capture_interval",
                0.25,
                3600.0,
            ),
            change_threshold=_number(
                screen["change_threshold"],
                "screen.change_threshold",
                0.0,
                1.0,
            ),
        ),
        ghost=GhostConfig(
            enabled=_boolean(sections["ghost"]["enabled"], "ghost.enabled"),
        ),
        ocr=OCRConfig(
            enabled=_boolean(sections["ocr"]["enabled"], "ocr.enabled"),
        ),
        voice=VoiceConfig(
            enabled=_boolean(sections["voice"]["enabled"], "voice.enabled"),
        ),
        privacy=PrivacyConfig(
            save_screenshots=_boolean(
                sections["privacy"]["save_screenshots"],
                "privacy.save_screenshots",
            ),
        ),
    )


def _write_initial_config(path: Path) -> None:
    """Write defaults through a temporary file to avoid partial YAML."""
    temporary_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".config-",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(config_to_yaml(AppConfig()))
            stream.flush()
            os.fsync(stream.fileno())

        # Another instance may have created the configuration during startup.
        if not path.exists():
            os.replace(temporary_path, path)
    except OSError as exc:
        raise ConfigError("Unable to create the user configuration.") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def load_config(
    path: Path,
    *,
    create_if_missing: bool = False,
) -> AppConfig:
    """Load a configuration without silently repairing invalid files."""
    if create_if_missing and not path.exists():
        _write_initial_config(path)

    try:
        with path.open("rb") as stream:
            encoded = stream.read(MAX_CONFIG_BYTES + 1)
    except OSError as exc:
        raise ConfigError("Unable to read the configuration file.") from exc

    if len(encoded) > MAX_CONFIG_BYTES:
        raise ConfigError("Configuration exceeds the 64 KiB size limit.")

    try:
        text = encoded.decode("utf-8-sig")
        document = yaml.load(text, Loader=StrictSafeLoader)
    except ConfigError:
        raise
    except (UnicodeError, yaml.YAMLError, RecursionError) as exc:
        raise ConfigError(
            "Configuration must contain valid UTF-8 YAML."
        ) from exc

    return parse_config(document)
