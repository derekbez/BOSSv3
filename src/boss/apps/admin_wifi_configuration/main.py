"""WiFi Configuration — view / connect to WiFi networks.

On a real Pi this uses ``nmcli`` to scan for networks and display the
current connection.  On dev mode it shows an informational message.

Full WiFi management with password entry is available at ``/admin/wifi``
in the NiceGUI admin panel.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from typing import TYPE_CHECKING

from boss.apps._lib.net_utils import get_local_ip

_log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def _has_nmcli() -> bool:
    """Check if nmcli is available on the system."""
    return shutil.which("nmcli") is not None


def _get_current_wifi() -> str | None:
    """Return the current active WiFi SSID, or None."""
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 2 and "wireless" in parts[1].lower():
                return parts[0]
    except Exception as exc:
        _log.debug("Failed to get current WiFi: %s", exc)
    return None


def _scan_networks() -> list[dict[str, str]]:
    """Scan for available WiFi networks. Returns list of {ssid, signal, security}."""
    networks: list[dict[str, str]] = []
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "yes"],
            capture_output=True, text=True, timeout=30,
        )
        seen: set[str] = set()
        for line in result.stdout.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[0] and parts[0] not in seen:
                seen.add(parts[0])
                networks.append({
                    "ssid": parts[0],
                    "signal": parts[1],
                    "security": parts[2] if parts[2] else "Open",
                })
        # Sort by signal strength descending
        networks.sort(key=lambda n: int(n["signal"] or "0"), reverse=True)
    except Exception as exc:
        _log.debug("WiFi scan failed: %s", exc)
    return networks


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    """Display WiFi status and available networks on the kiosk screen."""
    port = api.get_webui_port()
    ip = get_local_ip()

    if api.is_dev_mode() or not _has_nmcli():
        api.screen.display_html(
            f"""
            <div style="text-align: center; padding: 40px; color: #ffffff;">
                <h1 style="font-size: 28px; margin-bottom: 20px;">📶 WiFi Configuration</h1>
                <p style="font-size: 16px; color: #cccccc; margin-bottom: 20px;">
                    WiFi management requires a Raspberry Pi with nmcli.
                </p>
                <p style="font-size: 14px; color: #888888;">
                    For full WiFi configuration, open<br>
                    <span style="color: #00aaff; font-family: monospace;">
                        http://{ip}:{port}/admin/wifi
                    </span><br>
                    in a browser on the same network.
                </p>
                <p style="font-size: 14px; color: #888888; margin-top: 20px;">
                    Press any button to return.
                </p>
            </div>
            """
        )
        stop_event.wait()
        return

    # On Pi with nmcli available
    current = _get_current_wifi()
    networks = _scan_networks()

    # Build network list HTML
    net_rows = ""
    for i, net in enumerate(networks[:10]):
        highlight = "color: #00ff00; font-weight: bold;" if net["ssid"] == current else "color: #ffffff;"
        marker = " ◀ connected" if net["ssid"] == current else ""
        net_rows += (
            f'<tr><td style="padding: 4px 12px; {highlight}">{net["ssid"]}{marker}</td>'
            f'<td style="padding: 4px 12px; color: #cccccc;">{net["signal"]}%</td>'
            f'<td style="padding: 4px 12px; color: #cccccc;">{net["security"]}</td></tr>'
        )

    status_line = f"Connected to: <b style='color: #00ff00;'>{current}</b>" if current else "Not connected to WiFi"

    api.screen.display_html(
        f"""
        <div style="padding: 20px; color: #ffffff;">
            <h2 style="font-size: 22px; margin-bottom: 10px;">📶 WiFi Configuration</h2>
            <p style="font-size: 16px; margin-bottom: 10px;">{status_line}</p>
            <p style="font-size: 13px; color: #888888; margin-bottom: 15px;">
                IP: {ip} &nbsp;|&nbsp; To connect/change: open
                <span style="color: #00aaff; font-family: monospace;">http://{ip}:{port}/admin/wifi</span>
            </p>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <tr style="border-bottom: 1px solid #555;">
                    <th style="text-align: left; padding: 6px 12px; color: #00aaff;">Network</th>
                    <th style="text-align: left; padding: 6px 12px; color: #00aaff;">Signal</th>
                    <th style="text-align: left; padding: 6px 12px; color: #00aaff;">Security</th>
                </tr>
                {net_rows}
            </table>
            <p style="font-size: 13px; color: #666666; margin-top: 15px;">
                Press any button to return.
            </p>
        </div>
        """
    )

    stop_event.wait()
