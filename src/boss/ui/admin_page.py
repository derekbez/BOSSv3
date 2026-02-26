"""Admin page — NiceGUI ``/admin`` route for system management.

Provides:
* System status (hostname, uptime, Python version, dev_mode, current app)
* App list with switch mappings and required_env status
* Log viewer (tail of boss.log with auto-refresh)
* Git update button (guarded by dev_mode)
* Secrets status overview
* WiFi management subpage at ``/admin/wifi``
"""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

from nicegui import ui

if TYPE_CHECKING:
    from boss.config.secrets_manager import SecretsManager
    from boss.core.app_manager import AppManager
    from boss.core.app_runner import AppRunner
    from boss.core.event_bus import EventBus
    from boss.core.models.config import BossConfig

_log = logging.getLogger(__name__)

_BOOT_TIME = time.time()


class AdminPage:
    """Constructs the ``/admin`` route.

    Args:
        event_bus: Global event bus.
        config: System configuration.
        app_manager: App discovery and mapping manager.
        app_runner: Current app runner (for status).
        secrets: Secrets manager for key validation.
    """

    def __init__(
        self,
        event_bus: "EventBus",
        config: "BossConfig",
        app_manager: "AppManager",
        app_runner: "AppRunner",
        secrets: "SecretsManager",
    ) -> None:
        self._bus = event_bus
        self._config = config
        self._app_manager = app_manager
        self._app_runner = app_runner
        self._secrets = secrets

    def setup_page(self) -> None:
        """Register the ``/admin`` and ``/admin/wifi`` routes."""

        @ui.page("/admin")
        def admin_index():
            self._build_page()

        @ui.page("/admin/wifi")
        def admin_wifi():
            self._build_wifi_page()

    # ------------------------------------------------------------------
    # Page construction
    # ------------------------------------------------------------------

    def _build_page(self) -> None:
        """Construct the admin dashboard."""
        ui.dark_mode().enable()
        ui.query("body").style("background: #1a1a1a; margin: 0; padding: 0;")

        with ui.column().classes("w-full items-center").style(
            "min-height: 100vh; padding: 16px; gap: 16px; max-width: 960px; margin: auto;"
        ):
            # Header
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("BOSS Admin").style(
                    "font-size: 24px; font-weight: bold; color: #ffffff;"
                )
                ui.link("← Back to BOSS", "/").style("color: #00aaff;")

            # Cards
            self._build_status_card()
            self._build_app_list_card()
            self._build_log_viewer_card()
            self._build_secrets_card()
            self._build_wifi_link_card()
            if not self._config.system.dev_mode:
                self._build_git_update_card()

    # ------------------------------------------------------------------
    # Status card
    # ------------------------------------------------------------------

    def _build_status_card(self) -> None:
        with ui.card().classes("w-full").style("background: #2a2a2a;"):
            ui.label("System Status").style(
                "font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 8px;"
            )
            uptime_secs = int(time.time() - _BOOT_TIME)
            hours, remainder = divmod(uptime_secs, 3600)
            minutes, secs = divmod(remainder, 60)
            uptime_str = f"{hours}h {minutes}m {secs}s"

            current_app = "—"
            if self._app_runner and self._app_runner.is_running:
                current_app = getattr(self._app_runner, "_app_name", None) or "unknown"

            rows = [
                ("Hostname", platform.node()),
                ("Python", platform.python_version()),
                ("BOSS uptime", uptime_str),
                ("Dev mode", str(self._config.system.dev_mode)),
                ("Hardware", "mock" if self._config.system.dev_mode else "gpio"),
                ("Current app", current_app),
                ("Port", str(self._config.system.webui_port)),
            ]

            with ui.element("div").style(
                "display: grid; grid-template-columns: 150px 1fr; gap: 4px 16px;"
            ):
                for label, value in rows:
                    ui.label(label).style("color: #888888; font-size: 14px;")
                    ui.label(value).style("color: #ffffff; font-size: 14px;")

    # ------------------------------------------------------------------
    # App list card
    # ------------------------------------------------------------------

    def _build_app_list_card(self) -> None:
        with ui.card().classes("w-full").style("background: #2a2a2a;"):
            ui.label("Installed Apps").style(
                "font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 8px;"
            )

            manifests = self._app_manager.get_all_manifests()
            # Build reverse switch map
            switch_map: dict[str, list[int]] = {}
            for sw_val in range(256):
                name = self._app_manager.get_app_for_switch(sw_val)
                if name:
                    switch_map.setdefault(name, []).append(sw_val)

            columns = [
                {"name": "switch", "label": "Switch", "field": "switch", "align": "left"},
                {"name": "name", "label": "App", "field": "name", "align": "left"},
                {"name": "description", "label": "Description", "field": "description", "align": "left"},
                {"name": "env", "label": "Env Keys", "field": "env", "align": "left"},
            ]

            rows = []
            for app_name in sorted(manifests):
                manifest = manifests[app_name]
                sw_vals = switch_map.get(app_name, [])
                sw_str = ", ".join(str(v) for v in sw_vals) if sw_vals else "—"
                env_status = ""
                if manifest.required_env:
                    statuses = []
                    for key in manifest.required_env:
                        val = self._secrets.get(key)
                        icon = "✓" if val else "✗"
                        statuses.append(f"{icon} {key}")
                    env_status = ", ".join(statuses)
                else:
                    env_status = "none"
                rows.append({
                    "switch": sw_str,
                    "name": app_name,
                    "description": manifest.description[:60],
                    "env": env_status,
                })

            ui.table(columns=columns, rows=rows, row_key="name").classes(
                "w-full"
            ).style("background: #333333; color: #ffffff;")

    # ------------------------------------------------------------------
    # Log viewer card
    # ------------------------------------------------------------------

    def _build_log_viewer_card(self) -> None:
        with ui.card().classes("w-full").style("background: #2a2a2a;"):
            ui.label("Log Viewer").style(
                "font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 8px;"
            )

            log_path = Path(self._config.system.log_dir) / "boss.log"
            log_area = ui.log(max_lines=200).classes("w-full").style(
                "height: 300px; background: #111111; color: #cccccc; "
                "font-family: 'Courier New', monospace; font-size: 12px;"
            )

            def _load_log() -> None:
                log_area.clear()
                if log_path.is_file():
                    try:
                        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                        for line in lines[-200:]:
                            log_area.push(line)
                    except Exception as exc:
                        log_area.push(f"Error reading log: {exc}")
                else:
                    log_area.push(f"Log file not found: {log_path}")

            _load_log()
            auto_timer = ui.timer(5.0, _load_log, active=False)

            with ui.row().classes("gap-2"):
                ui.button("Refresh", on_click=_load_log, icon="refresh").props("flat color=primary")

                def _toggle_auto(e) -> None:
                    auto_timer.active = e.value

                ui.switch("Auto-refresh (5s)", on_change=_toggle_auto).style("color: #ffffff;")

    # ------------------------------------------------------------------
    # Secrets status card
    # ------------------------------------------------------------------

    def _build_secrets_card(self) -> None:
        with ui.card().classes("w-full").style("background: #2a2a2a;"):
            ui.label("Secrets Status").style(
                "font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 8px;"
            )

            # Collect all required_env keys across all apps
            all_keys: dict[str, list[str]] = {}  # key → [app_names]
            for app_name, manifest in self._app_manager.get_all_manifests().items():
                for key in manifest.required_env:
                    all_keys.setdefault(key, []).append(app_name)

            if not all_keys:
                ui.label("No apps require API keys.").style("color: #888888;")
                return

            with ui.element("div").style(
                "display: grid; grid-template-columns: auto 40px 1fr; gap: 4px 16px; align-items: center;"
            ):
                for key in sorted(all_keys):
                    val = self._secrets.get(key)
                    is_set = bool(val)
                    apps = ", ".join(sorted(all_keys[key]))
                    ui.label(key).style(
                        "color: #ffffff; font-family: monospace; font-size: 13px;"
                    )
                    ui.label("✓" if is_set else "✗").style(
                        f"color: {'#44ff44' if is_set else '#ff4444'}; font-weight: bold;"
                    )
                    ui.label(apps).style("color: #888888; font-size: 12px;")

    # ------------------------------------------------------------------
    # Git update card
    # ------------------------------------------------------------------

    def _build_git_update_card(self) -> None:
        with ui.card().classes("w-full").style("background: #2a2a2a;"):
            ui.label("Software Update").style(
                "font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 8px;"
            )

            output_area = ui.log(max_lines=50).classes("w-full").style(
                "height: 150px; background: #111111; color: #cccccc; "
                "font-family: 'Courier New', monospace; font-size: 12px;"
            )
            output_area.push("Click 'git pull' to check for updates.")

            def _run_git_pull() -> None:
                output_area.clear()
                output_area.push("Running git pull …")
                try:
                    result = subprocess.run(
                        ["git", "pull"],
                        cwd="/opt/boss",
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    for line in result.stdout.splitlines():
                        output_area.push(line)
                    if result.stderr:
                        for line in result.stderr.splitlines():
                            output_area.push(f"stderr: {line}")
                    output_area.push(f"Exit code: {result.returncode}")
                except Exception as exc:
                    output_area.push(f"Error: {exc}")

            ui.button("git pull", on_click=_run_git_pull, icon="download").props(
                "color=warning"
            )

    # ------------------------------------------------------------------
    # WiFi link card (on admin page)
    # ------------------------------------------------------------------

    def _build_wifi_link_card(self) -> None:
        with ui.card().classes("w-full").style("background: #2a2a2a;"):
            with ui.row().classes("items-center gap-4"):
                ui.icon("wifi").style("color: #00aaff; font-size: 24px;")
                ui.label("WiFi Configuration").style(
                    "font-size: 18px; font-weight: bold; color: #ffffff;"
                )
                ui.link("Open WiFi Manager →", "/admin/wifi").style(
                    "color: #00aaff; font-size: 14px;"
                )

    # ------------------------------------------------------------------
    # WiFi management page (/admin/wifi)
    # ------------------------------------------------------------------

    def _build_wifi_page(self) -> None:
        """Construct the WiFi management page."""
        ui.dark_mode().enable()
        ui.query("body").style("background: #1a1a1a; margin: 0; padding: 0;")

        with ui.column().classes("w-full items-center").style(
            "min-height: 100vh; padding: 16px; gap: 16px; max-width: 960px; margin: auto;"
        ):
            # Header
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("WiFi Configuration").style(
                    "font-size: 24px; font-weight: bold; color: #ffffff;"
                )
                ui.link("← Back to Admin", "/admin").style("color: #00aaff;")

            has_nmcli = shutil.which("nmcli") is not None

            if self._config.system.dev_mode or not has_nmcli:
                with ui.card().classes("w-full").style("background: #2a2a2a;"):
                    ui.label(
                        "WiFi management requires a Raspberry Pi with nmcli installed."
                    ).style("color: #cccccc; font-size: 16px;")
                    if self._config.system.dev_mode:
                        ui.label("(dev_mode is enabled)").style(
                            "color: #888888; font-size: 14px;"
                        )
                return

            # --- Current connection ---
            self._build_wifi_current_card()

            # --- Available networks + connect form ---
            self._build_wifi_networks_card()

    def _build_wifi_current_card(self) -> None:
        """Show the current WiFi connection status."""
        with ui.card().classes("w-full").style("background: #2a2a2a;"):
            ui.label("Current Connection").style(
                "font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 8px;"
            )

            current_label = ui.label("Scanning …").style(
                "color: #cccccc; font-size: 16px;"
            )

            def _refresh_current() -> None:
                try:
                    result = subprocess.run(
                        ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"],
                        capture_output=True, text=True, timeout=10,
                    )
                    for line in result.stdout.strip().splitlines():
                        parts = line.split(":")
                        if len(parts) >= 2 and "wireless" in parts[1].lower():
                            current_label.text = f"Connected to: {parts[0]}"
                            current_label.style("color: #44ff44; font-size: 16px;")
                            return
                    current_label.text = "Not connected to WiFi"
                    current_label.style("color: #ff4444; font-size: 16px;")
                except Exception as exc:
                    current_label.text = f"Error: {exc}"
                    current_label.style("color: #ff4444; font-size: 16px;")

            _refresh_current()

    def _build_wifi_networks_card(self) -> None:
        """Show available networks and a connect form."""
        with ui.card().classes("w-full").style("background: #2a2a2a;"):
            ui.label("Available Networks").style(
                "font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 8px;"
            )

            networks_container = ui.column().classes("w-full gap-2")
            status_label = ui.label("").style("color: #cccccc; font-size: 14px;")

            # Connect form
            ui.separator().style("background: #444444;")
            ui.label("Connect to a Network").style(
                "font-size: 16px; font-weight: bold; color: #ffffff; margin-top: 8px;"
            )

            ssid_input = ui.input("SSID", placeholder="Network name").classes("w-full")
            password_input = ui.input(
                "Password", placeholder="Network password", password=True, password_toggle_button=True
            ).classes("w-full")

            def _scan_networks() -> None:
                networks_container.clear()
                status_label.text = "Scanning …"
                try:
                    result = subprocess.run(
                        ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "yes"],
                        capture_output=True, text=True, timeout=30,
                    )
                    seen: set[str] = set()
                    nets: list[tuple[str, str, str]] = []
                    for line in result.stdout.strip().splitlines():
                        parts = line.split(":")
                        if len(parts) >= 3 and parts[0] and parts[0] not in seen:
                            seen.add(parts[0])
                            nets.append((parts[0], parts[1], parts[2] or "Open"))
                    nets.sort(key=lambda n: int(n[1] or "0"), reverse=True)

                    with networks_container:
                        for ssid, signal, security in nets[:15]:
                            with ui.row().classes("items-center gap-2").style(
                                "padding: 4px 0;"
                            ):
                                ui.label(f"📶 {ssid}").style(
                                    "color: #ffffff; font-size: 14px; min-width: 200px;"
                                )
                                ui.label(f"{signal}%").style(
                                    "color: #888888; font-size: 13px; min-width: 50px;"
                                )
                                ui.label(security).style(
                                    "color: #888888; font-size: 13px; min-width: 100px;"
                                )
                                ui.button(
                                    "Select",
                                    on_click=lambda s=ssid: ssid_input.set_value(s),
                                ).props("flat dense color=primary size=sm")

                    status_label.text = f"Found {len(nets)} networks"
                except Exception as exc:
                    status_label.text = f"Scan error: {exc}"

            _scan_networks()

            def _connect() -> None:
                ssid = ssid_input.value.strip()
                password = password_input.value
                if not ssid:
                    status_label.text = "Please enter an SSID"
                    return

                status_label.text = f"Connecting to {ssid} …"
                try:
                    cmd = ["nmcli", "device", "wifi", "connect", ssid]
                    if password:
                        cmd += ["password", password]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=30,
                    )
                    if result.returncode == 0:
                        status_label.text = f"✓ Connected to {ssid}"
                        status_label.style("color: #44ff44; font-size: 14px;")
                    else:
                        err = result.stderr.strip() or result.stdout.strip()
                        status_label.text = f"✗ Failed: {err}"
                        status_label.style("color: #ff4444; font-size: 14px;")
                except Exception as exc:
                    status_label.text = f"✗ Error: {exc}"
                    status_label.style("color: #ff4444; font-size: 14px;")

            with ui.row().classes("gap-2"):
                ui.button("Scan", on_click=_scan_networks, icon="refresh").props(
                    "flat color=primary"
                )
                ui.button("Connect", on_click=_connect, icon="wifi").props(
                    "color=positive"
                )

