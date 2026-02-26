"""Config manager — load JSON → apply env overrides → validate → BossConfig."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from boss.core.models.config import BossConfig

_log = logging.getLogger(__name__)

# Default config file, relative to the project root (where pyproject.toml lives).
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "boss_config.json"

# Environment variable → config field mapping.
# Keys are env-var names; values are ``(section, field)`` tuples.
_ENV_OVERRIDES: dict[str, tuple[str, str, type]] = {
    "BOSS_LOG_LEVEL": ("system", "log_level", str),
    "BOSS_DEV_MODE": ("system", "dev_mode", bool),
    "BOSS_TEST_MODE": ("system", "test_mode", bool),
    "BOSS_WEBUI_PORT": ("system", "webui_port", int),
}


def _coerce(value: str, target_type: type) -> object:
    """Coerce a string env-var value to the expected Python type."""
    if target_type is bool:
        return value.strip().lower() in ("1", "true", "yes")
    return target_type(value)


def load_config(config_path: Path | str | None = None) -> BossConfig:
    """Load, override, and validate the BOSS configuration.

    Args:
        config_path: Path to ``boss_config.json``.  When *None*, falls back
            to ``BOSS_CONFIG_FILE`` env-var and then the default location
            next to this module.

    Returns:
        A fully-validated :class:`BossConfig` instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
    """
    path = _resolve_config_path(config_path)
    _log.info("Loading config from %s", path)

    raw = json.loads(path.read_text(encoding="utf-8"))

    # Apply env overrides ------------------------------------------------
    for env_key, (section, field, typ) in _ENV_OVERRIDES.items():
        env_val = os.environ.get(env_key)
        if env_val is not None:
            raw.setdefault(section, {})[field] = _coerce(env_val, typ)
            _log.debug("Env override: %s → %s.%s = %r", env_key, section, field, env_val)

    return BossConfig(**raw)


def save_system_location(
    lat: float,
    lon: float,
    config_path: Path | str | None = None,
) -> BossConfig:
    """Persist ``system.location`` and return validated config.

    The config file path resolution matches :func:`load_config`.
    """
    path = _resolve_config_path(config_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw.setdefault("system", {})["location"] = {"lat": float(lat), "lon": float(lon)}

    validated = BossConfig(**raw)
    _atomic_write_json(path, validated.model_dump())
    return validated


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with open(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        Path(tmp_name).replace(path)
    finally:
        tmp_path = Path(tmp_name)
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _resolve_config_path(config_path: Path | str | None) -> Path:
    if config_path is not None:
        p = Path(config_path)
    else:
        env = os.environ.get("BOSS_CONFIG_FILE")
        p = Path(env) if env else _DEFAULT_CONFIG_PATH
    if not p.is_file():
        raise FileNotFoundError(
            f"Config file not found: {p}\n"
            "Create boss_config.json or set BOSS_CONFIG_FILE to a valid path."
        )
    return p
