"""Test helpers — temporary mini-app scaffolding."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def create_app(
    base_dir: Path,
    name: str,
    code: str = 'def run(stop_event, api):\n    stop_event.wait(0.1)\n',
    manifest_overrides: dict[str, Any] | None = None,
) -> Path:
    """Create a mini-app directory with ``main.py`` and ``manifest.json``.

    Returns the path to the app directory.
    """
    app_dir = base_dir / name
    app_dir.mkdir(parents=True, exist_ok=True)

    (app_dir / "main.py").write_text(code, encoding="utf-8")

    manifest: dict[str, Any] = {
        "name": name.replace("_", " ").title(),
        "description": f"Test app {name}",
        "version": "1.0.0",
    }
    if manifest_overrides:
        manifest.update(manifest_overrides)

    (app_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return app_dir
