"""Tests for admin_boss_admin mini-app."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from boss.apps.admin_boss_admin.main import run, _get_local_ip


class TestAdminBossAdmin:
    """Unit tests for the admin panel mini-app."""

    def test_run_displays_admin_url(self) -> None:
        """The app should display the /admin URL on screen."""
        api = MagicMock()
        api.get_webui_port.return_value = 8080
        stop = threading.Event()
        stop.set()  # Pre-set so run() returns immediately

        run(stop, api)

        api.screen.display_html.assert_called_once()
        html = api.screen.display_html.call_args[0][0]
        assert "/admin" in html
        assert "8080" in html

    def test_run_uses_configured_port(self) -> None:
        """Should use the webui_port from config."""
        api = MagicMock()
        api.get_webui_port.return_value = 9999
        stop = threading.Event()
        stop.set()

        run(stop, api)

        html = api.screen.display_html.call_args[0][0]
        assert "9999" in html

    def test_get_local_ip_returns_string(self) -> None:
        """_get_local_ip should return a string."""
        result = _get_local_ip()
        assert isinstance(result, str)

    def test_get_local_ip_fallback_on_error(self) -> None:
        """If socket fails, should return 'localhost'."""
        with patch("boss.apps.admin_boss_admin.main.socket.socket") as mock_sock:
            mock_sock.side_effect = OSError("no network")
            result = _get_local_ip()
            assert result == "localhost"

    def test_run_waits_for_stop_event(self) -> None:
        """The app should block on stop_event.wait()."""
        api = MagicMock()
        api.get_webui_port.return_value = 8080
        stop = threading.Event()

        # Run in a thread and verify it blocks
        t = threading.Thread(target=run, args=(stop, api), daemon=True)
        t.start()

        # Give it time to start
        import time
        time.sleep(0.1)
        assert t.is_alive()  # Should still be waiting

        stop.set()
        t.join(timeout=2)
        assert not t.is_alive()
