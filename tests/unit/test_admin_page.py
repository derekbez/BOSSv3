"""Tests for the AdminPage class."""

from __future__ import annotations

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
