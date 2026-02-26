"""Tests for the AdminPage class."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from boss.ui.admin_page import AdminPage


class TestAdminPage:
    """Unit tests for AdminPage construction and properties."""

    def _make_admin_page(self) -> AdminPage:
        """Create an AdminPage with mock dependencies."""
        bus = MagicMock()
        config = MagicMock()
        config.system.dev_mode = True
        config.system.webui_port = 8080
        config.system.log_dir = "logs"
        app_manager = MagicMock()
        app_manager.get_all_manifests.return_value = {}
        app_manager.get_manifest.return_value = SimpleNamespace(config={})
        app_runner = MagicMock()
        app_runner.is_running = False
        secrets = MagicMock()
        return AdminPage(
            event_bus=bus,
            config=config,
            app_manager=app_manager,
            app_runner=app_runner,
            secrets=secrets,
        )

    def test_admin_page_init(self) -> None:
        """AdminPage should initialise without errors."""
        page = self._make_admin_page()
        assert page is not None

    def test_admin_page_has_setup_page(self) -> None:
        """AdminPage should have a setup_page method."""
        page = self._make_admin_page()
        assert hasattr(page, "setup_page")
        assert callable(page.setup_page)

    def test_admin_page_stores_dependencies(self) -> None:
        """AdminPage should store all injected dependencies."""
        page = self._make_admin_page()
        assert page._bus is not None
        assert page._config is not None
        assert page._app_manager is not None
        assert page._app_runner is not None
        assert page._secrets is not None

    def test_save_location_values_success(self) -> None:
        page = self._make_admin_page()
        with patch("boss.ui.admin_page.save_system_location") as mock_save:
            mock_save.return_value = SimpleNamespace(
                system=SimpleNamespace(location=SimpleNamespace(lat=51.0, lon=-1.0))
            )
            ok, message = page._save_location_values("51.0", "-1.0")

        assert ok is True
        assert "Location saved" in message
        assert page._config.system.location.lat == 51.0
        assert page._config.system.location.lon == -1.0

    def test_save_location_values_rejects_invalid(self) -> None:
        page = self._make_admin_page()
        ok, message = page._save_location_values("north", "west")
        assert ok is False
        assert "numeric" in message

    def test_save_countdown_overrides_success(self) -> None:
        page = self._make_admin_page()
        with patch("boss.ui.admin_page.set_app_overrides") as mock_set:
            ok, message = page._save_countdown_overrides(
                event_name="Launch",
                target_date="2026-07-01",
                target_time="09:15:00",
                refresh_seconds="15",
            )

        assert ok is True
        assert "saved" in message
        mock_set.assert_called_once()

    def test_save_countdown_overrides_rejects_bad_date(self) -> None:
        page = self._make_admin_page()
        ok, message = page._save_countdown_overrides(
            event_name="Launch",
            target_date="07/01/2026",
            target_time="09:15:00",
            refresh_seconds="15",
        )
        assert ok is False
        assert "YYYY-MM-DD" in message

    def test_reset_countdown_overrides_success(self) -> None:
        page = self._make_admin_page()
        with patch("boss.ui.admin_page.clear_app_overrides") as mock_clear:
            ok, message = page._reset_countdown_overrides()

        assert ok is True
        assert "reset" in message
        mock_clear.assert_called_once_with("countdown_to_event")

    def test_save_secret_value_success(self) -> None:
        page = self._make_admin_page()
        ok, message = page._save_secret_value("BOSS_APP_KEY", "abc")
        assert ok is True
        assert "Saved secret" in message
        page._secrets.set.assert_called_once_with("BOSS_APP_KEY", "abc")

    def test_delete_secret_value_not_found(self) -> None:
        page = self._make_admin_page()
        page._secrets.delete.return_value = False
        ok, message = page._delete_secret_value("BOSS_APP_KEY")
        assert ok is False
        assert "not found" in message

    def test_check_for_updates_success(self) -> None:
        page = self._make_admin_page()
        with patch.object(page, "_run_git_command") as mock_git:
            mock_git.side_effect = [
                (0, "", ""),
                (0, "## main...origin/main", ""),
                (0, "abc123 Update note", ""),
            ]
            ok, lines = page._check_for_updates()

        assert ok is True
        assert any("Commits available upstream" in line for line in lines)

    def test_apply_git_update_failure(self) -> None:
        page = self._make_admin_page()
        with patch.object(page, "_run_git_command") as mock_git:
            mock_git.return_value = (1, "", "fatal: not a git repository")
            ok, lines = page._apply_git_update()

        assert ok is False
        assert any("Exit code: 1" in line for line in lines)
