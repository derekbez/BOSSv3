"""Tests for validate_manifests.py script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_manifests.py"


class TestValidateManifestsScript:
    """Integration-style tests for the manifest validation script."""

    def test_script_exists(self) -> None:
        assert SCRIPT.is_file()

    def test_script_runs_successfully(self) -> None:
        """The script should exit 0 on the real app tree."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Script failed:\n{result.stdout}\n{result.stderr}"
        assert "All checks passed" in result.stdout

    def test_script_finds_all_apps(self) -> None:
        """Should discover at least 31 apps (29 original + 2 admin)."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert "Apps discovered: 31" in result.stdout

    def test_script_reports_switch_mappings(self) -> None:
        """Should report switch mappings."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert "Switch mapping cross-reference" in result.stdout
