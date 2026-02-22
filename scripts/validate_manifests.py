#!/usr/bin/env python3
"""Validate all mini-app manifests using Pydantic models.

Usage:
    python scripts/validate_manifests.py

Checks performed:
  - Every ``apps/*/manifest.json`` parses and validates via ``AppManifest``
  - ``entry_point`` file exists in the app directory
  - The app defines a ``run()`` callable
  - Cross-references ``app_mappings.json`` -- reports unmapped / invalid mappings
  - Reports ``required_env`` keys and whether they appear in ``secrets.sample.env``

Exit code: 0 if all checks pass, 1 otherwise.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

# Resolve project root (script lives in scripts/, project root is parent)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

# Ensure src/ is on sys.path so boss.* imports work
sys.path.insert(0, str(SRC_DIR))

from boss.core.models.manifest import AppManifest, migrate_manifest_v2  # noqa: E402

# ---------------------------------------------------------------------------
# Colour helpers (ANSI)
# ---------------------------------------------------------------------------
_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_BOLD = "\033[1m"
_RESET = "\033[0m"

# Use ASCII-safe symbols to avoid cp1252 encoding errors on Windows
_CHECK = "[OK]"
_CROSS = "[FAIL]"
_WARN_SYM = "[WARN]"


def _pass(msg: str) -> None:
    print(f"  {_GREEN}{_CHECK}{_RESET} {msg}")


def _fail(msg: str) -> None:
    print(f"  {_RED}{_CROSS}{_RESET} {msg}")


def _warn(msg: str) -> None:
    print(f"  {_YELLOW}{_WARN_SYM}{_RESET} {msg}")


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _load_secrets_keys() -> set[str]:
    """Return the set of key names defined in ``secrets.sample.env``."""
    sample = PROJECT_ROOT / "secrets" / "secrets.sample.env"
    keys: set[str] = set()
    if not sample.is_file():
        return keys
    for line in sample.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key = line.split("=", 1)[0].strip()
        if key:
            keys.add(key)
    return keys


def _load_mappings(apps_dir: Path) -> dict[int, str]:
    """Load ``app_mappings.json`` and return switch->app_name."""
    mappings_path = SRC_DIR / "boss" / "config" / "app_mappings.json"
    if not mappings_path.is_file():
        return {}
    raw = json.loads(mappings_path.read_text(encoding="utf-8"))
    mapping_data = raw.get("app_mappings", raw)
    result: dict[int, str] = {}
    for key, app_name in mapping_data.items():
        try:
            result[int(key)] = app_name
        except ValueError:
            pass
    return result


def _check_run_function(app_dir: Path, entry_point: str) -> bool:
    """Return True if the entry_point module defines a ``run`` callable."""
    ep_path = app_dir / entry_point
    if not ep_path.is_file():
        return False
    try:
        spec = importlib.util.spec_from_file_location(app_dir.name, ep_path)
        if spec is None or spec.loader is None:
            return False
        mod = importlib.util.module_from_spec(spec)
        # Don't execute, just check if 'run' is loadable
        # We'll do a simpler text-based check
        source = ep_path.read_text(encoding="utf-8")
        return "def run(" in source
    except Exception:
        return False


def validate_all() -> bool:
    """Run all validation checks.  Returns True if everything passes."""
    apps_dir = SRC_DIR / "boss" / "apps"
    if not apps_dir.is_dir():
        print(f"{_RED}ERROR: apps directory not found: {apps_dir}{_RESET}")
        return False

    secrets_keys = _load_secrets_keys()
    switch_map = _load_mappings(apps_dir)
    mapped_apps = set(switch_map.values())

    all_ok = True
    discovered_apps: set[str] = set()

    # --- Validate each app ---
    app_dirs = sorted(
        d for d in apps_dir.iterdir()
        if d.is_dir() and not d.name.startswith("_")
    )

    print(f"\n{_BOLD}Validating {len(app_dirs)} mini-apps{_RESET}\n")

    for app_dir in app_dirs:
        manifest_path = app_dir / "manifest.json"
        app_name = app_dir.name
        discovered_apps.add(app_name)
        print(f"{_BOLD}{app_name}{_RESET}")

        # 1. manifest.json exists
        if not manifest_path.is_file():
            _fail("manifest.json not found")
            all_ok = False
            continue

        # 2. JSON is valid and parses
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            _fail(f"invalid JSON: {exc}")
            all_ok = False
            continue

        # 3. Migrate and validate via Pydantic
        try:
            raw = migrate_manifest_v2(raw)
            manifest = AppManifest(**raw)
        except Exception as exc:
            _fail(f"Pydantic validation failed: {exc}")
            all_ok = False
            continue
        _pass("manifest.json valid")

        # 4. Entry point exists
        ep_path = app_dir / manifest.entry_point
        if ep_path.is_file():
            _pass(f"entry_point '{manifest.entry_point}' exists")
        else:
            _fail(f"entry_point '{manifest.entry_point}' NOT FOUND")
            all_ok = False

        # 5. run() function defined
        if _check_run_function(app_dir, manifest.entry_point):
            _pass("run() function defined")
        else:
            _fail("run() function NOT FOUND in entry point")
            all_ok = False

        # 6. Switch mapping
        if app_name in mapped_apps:
            sw_vals = [k for k, v in switch_map.items() if v == app_name]
            _pass(f"mapped to switch {sw_vals}")
        else:
            _warn("not mapped to any switch value")

        # 7. Required env keys
        if manifest.required_env:
            for key in manifest.required_env:
                if key in secrets_keys:
                    _pass(f"required_env '{key}' in secrets.sample.env")
                else:
                    _warn(f"required_env '{key}' NOT in secrets.sample.env")

    # --- Cross-reference mappings -> apps ---
    print(f"\n{_BOLD}Switch mapping cross-reference{_RESET}\n")

    for sw_val, app_name in sorted(switch_map.items()):
        if app_name in discovered_apps:
            _pass(f"switch {sw_val:3d} -> {app_name}")
        else:
            _fail(f"switch {sw_val:3d} -> {app_name} (app NOT FOUND)")
            all_ok = False

    # --- Summary ---
    print(f"\n{_BOLD}Summary{_RESET}")
    print(f"  Apps discovered: {len(discovered_apps)}")
    print(f"  Switch mappings: {len(switch_map)}")
    print(f"  Unmapped apps:   {len(discovered_apps - mapped_apps)}")
    if discovered_apps - mapped_apps:
        for name in sorted(discovered_apps - mapped_apps):
            _warn(f"  unmapped: {name}")

    return all_ok


if __name__ == "__main__":
    ok = validate_all()
    if ok:
        print(f"\n{_GREEN}{_BOLD}All checks passed{_RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{_RED}{_BOLD}Some checks failed{_RESET}\n")
        sys.exit(1)
