"""BOSS Admin Panel — directs user to the /admin NiceGUI route.

On the kiosk display this shows a message pointing the user to the
admin URL.  The actual admin panel lives at ``/admin`` and is rendered
by :class:`boss.ui.admin_page.AdminPage`.
"""

from __future__ import annotations

import socket
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def _get_local_ip() -> str:
    """Best-effort local IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "localhost"


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    """Show admin panel URL on the kiosk screen."""
    port = api.get_webui_port()
    ip = _get_local_ip()

    api.screen.display_html(
        f"""
        <div style="text-align: center; padding: 40px; color: #ffffff;">
            <h1 style="font-size: 28px; margin-bottom: 20px;">🔧 BOSS Admin Panel</h1>
            <p style="font-size: 18px; color: #cccccc; margin-bottom: 30px;">
                Open the admin dashboard in any browser on the same network:
            </p>
            <p style="font-size: 24px; color: #00aaff; font-family: monospace;
                      background: #333333; padding: 16px; border-radius: 8px;
                      display: inline-block;">
                http://{ip}:{port}/admin
            </p>
            <p style="font-size: 14px; color: #888888; margin-top: 30px;">
                Press any button to return.
            </p>
        </div>
        """
    )

    # Wait until stopped (any button press triggers stop via normal app lifecycle)
    stop_event.wait()
