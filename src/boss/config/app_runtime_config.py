"""Runtime app config overrides persisted to JSON.

This store is used for admin-edited app settings. App manifests remain
source-of-defaults, while this file contains user overrides keyed by app name.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

_DEFAULT_OVERRIDES_PATH = Path(__file__).resolve().parent / "app_runtime_overrides.json"


def _resolve_overrides_path(path: Path | str | None = None) -> Path:
    if path is not None:
        return Path(path)
    return _DEFAULT_OVERRIDES_PATH


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with open(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        Path(tmp_name).replace(path)
    finally:
        tmp_path = Path(tmp_name)
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def load_runtime_overrides(path: Path | str | None = None) -> dict[str, dict[str, Any]]:
    target = _resolve_overrides_path(path)
    if not target.is_file():
        return {}

    raw = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}

    result: dict[str, dict[str, Any]] = {}
    for app_name, values in raw.items():
        if isinstance(app_name, str) and isinstance(values, dict):
            result[app_name] = dict(values)
    return result


def get_app_overrides(app_name: str, path: Path | str | None = None) -> dict[str, Any]:
    return dict(load_runtime_overrides(path).get(app_name, {}))


def set_app_overrides(
    app_name: str,
    overrides: dict[str, Any],
    path: Path | str | None = None,
) -> None:
    if not app_name.strip():
        raise ValueError("app_name must be non-empty")
    if not isinstance(overrides, dict):
        raise TypeError("overrides must be a dict")

    data = load_runtime_overrides(path)
    data[app_name] = dict(overrides)
    _atomic_write_json(_resolve_overrides_path(path), data)


def clear_app_overrides(app_name: str, path: Path | str | None = None) -> None:
    data = load_runtime_overrides(path)
    if app_name in data:
        del data[app_name]
        _atomic_write_json(_resolve_overrides_path(path), data)
