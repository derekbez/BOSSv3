"""Tests for admin_wifi_configuration mini-app."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from boss.apps.admin_wifi_configuration.main import run, _has_nmcli
from boss.apps._lib.net_utils import get_local_ip


class TestAdminWifiConfiguration:
    """Unit tests for the WiFi configuration mini-app."""

    def test_run_dev_mode_shows_message(self) -> None:
        """In dev mode, should show a 'not available' message."""
        api = MagicMock()
        api.is_dev_mode.return_value = True
        api.get_webui_port.return_value = 8080
        stop = threading.Event()
        stop.set()

        run(stop, api)

        api.screen.display_html.assert_called_once()
        html = api.screen.display_html.call_args[0][0]
        assert "WiFi" in html
        assert "Raspberry Pi" in html or "nmcli" in html

    @patch("boss.apps.admin_wifi_configuration.main._has_nmcli", return_value=False)
    def test_run_no_nmcli_shows_message(self, mock_nmcli) -> None:
        """Without nmcli, should show a 'not available' message."""
        api = MagicMock()
        api.is_dev_mode.return_value = False
        api.get_webui_port.return_value = 8080
        stop = threading.Event()
        stop.set()

        run(stop, api)

        api.screen.display_html.assert_called_once()
        html = api.screen.display_html.call_args[0][0]
        assert "WiFi" in html

    def test_run_includes_admin_wifi_url(self) -> None:
        """Should include /admin/wifi URL in the output."""
        api = MagicMock()
        api.is_dev_mode.return_value = True
        api.get_webui_port.return_value = 8080
        stop = threading.Event()
        stop.set()

        run(stop, api)

        html = api.screen.display_html.call_args[0][0]
        assert "/admin/wifi" in html

    def test_get_local_ip_returns_string(self) -> None:
        """get_local_ip should return a string."""
        result = get_local_ip()
        assert isinstance(result, str)

    def test_has_nmcli_returns_bool(self) -> None:
        """_has_nmcli should return a boolean."""
        result = _has_nmcli()
        assert isinstance(result, bool)

    @patch("boss.apps.admin_wifi_configuration.main.shutil.which", return_value=None)
    def test_has_nmcli_false_when_not_found(self, mock_which) -> None:
        """_has_nmcli should return False when nmcli is not on PATH."""
        assert _has_nmcli() is False

    @patch("boss.apps.admin_wifi_configuration.main.shutil.which", return_value="/usr/bin/nmcli")
    def test_has_nmcli_true_when_found(self, mock_which) -> None:
        """_has_nmcli should return True when nmcli is found."""
        assert _has_nmcli() is True

    def test_run_waits_for_stop_event(self) -> None:
        """The app should block on stop_event.wait()."""
        api = MagicMock()
        api.is_dev_mode.return_value = True
        api.get_webui_port.return_value = 8080
        stop = threading.Event()

        t = threading.Thread(target=run, args=(stop, api), daemon=True)
        t.start()

        import time
        time.sleep(0.1)
        assert t.is_alive()

        stop.set()
        t.join(timeout=2)
        assert not t.is_alive()
