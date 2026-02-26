"""Admin page — NiceGUI ``/admin`` route for system management.

Provides:
* System status (hostname, uptime, Python version, dev_mode, current app)
* App list with switch mappings and required_env status
* Log viewer (tail of boss.log with auto-refresh)
* Git update button (guarded by dev_mode)
* Secrets status and editing
* WiFi management subpage at ``/admin/wifi``
"""

from __future__ import annotations

from datetime import date, time as dt_time
import json
import logging
import platform
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from nicegui import ui

from boss.config.app_runtime_config import (
    clear_app_overrides,
    get_app_overrides,
    set_app_overrides,
)
from boss.config.config_manager import save_system_location

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
            self._build_global_settings_card()
            self._build_app_config_card()
            self._build_app_list_card()
            self._build_app_management_card()
            self._build_log_viewer_card()
            self._build_secrets_card()
            self._build_wifi_link_card()
            if not self._config.system.dev_mode:
                self._build_git_update_card()

    def _build_global_settings_card(self) -> None:
        with ui.card().classes("w-full").style("background: #2a2a2a;"):
            ui.label("Global Settings").style(
                "font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 8px;"
            )
            ui.label("Location applies on next app launch.").style(
                "color: #888888; font-size: 13px;"
            )

            lat_input = ui.input(
                "Latitude",
                value=str(self._config.system.location.lat),
                placeholder="e.g. 51.8167",
            ).classes("w-full")
            lon_input = ui.input(
                "Longitude",
                value=str(self._config.system.location.lon),
                placeholder="e.g. -0.8146",
            ).classes("w-full")

            with ui.row().classes("gap-2"):
                def _save_location() -> None:
                    ok, message = self._save_location_values(lat_input.value, lon_input.value)
                    ui.notify(message, color="positive" if ok else "negative")

                ui.button("Save Location", on_click=_save_location, icon="save").props(
                    "color=primary"
                )

    def _build_app_config_card(self) -> None:
        with ui.card().classes("w-full").style("background: #2a2a2a;"):
            ui.label("App Config").style(
                "font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 8px;"
            )

            app_name = "countdown_to_event"
            manifest = self._app_manager.get_manifest(app_name)
            if manifest is None:
                ui.label("Countdown app manifest not found.").style(
                    "color: #ff4444; font-size: 14px;"
                )
                return

            effective = dict(manifest.config)
            effective.update(get_app_overrides(app_name))

            ui.label("Countdown to Event (applies on next launch)").style(
                "color: #cccccc; font-size: 14px; margin-bottom: 8px;"
            )

            event_name_input = ui.input(
                "Event Name",
                value=str(effective.get("event_name", "Event")),
            ).classes("w-full")
            target_date_input = ui.input(
                "Target Date (YYYY-MM-DD)",
                value=str(effective.get("target_date", "2026-12-25")),
            ).classes("w-full")
            target_time_input = ui.input(
                "Target Time (HH:MM:SS)",
                value=str(effective.get("target_time", "00:00:00")),
            ).classes("w-full")
            refresh_input = ui.input(
                "Refresh Seconds",
                value=str(effective.get("refresh_seconds", 30)),
            ).classes("w-full")

            with ui.row().classes("gap-2"):
                def _save_countdown() -> None:
                    ok, message = self._save_countdown_overrides(
                        event_name=event_name_input.value,
                        target_date=target_date_input.value,
                        target_time=target_time_input.value,
                        refresh_seconds=refresh_input.value,
                    )
                    ui.notify(message, color="positive" if ok else "negative")

                def _reset_countdown() -> None:
                    ok, message = self._reset_countdown_overrides()
                    if ok:
                        defaults = manifest.config
                        event_name_input.set_value(str(defaults.get("event_name", "Event")))
                        target_date_input.set_value(str(defaults.get("target_date", "2026-12-25")))
                        target_time_input.set_value(str(defaults.get("target_time", "00:00:00")))
                        refresh_input.set_value(str(defaults.get("refresh_seconds", 30)))
                    ui.notify(message, color="positive" if ok else "negative")

                ui.button("Save", on_click=_save_countdown, icon="save").props(
                    "color=primary"
                )
                ui.button("Reset to Defaults", on_click=_reset_countdown, icon="restart_alt").props(
                    "flat color=warning"
                )

    def _save_location_values(self, lat: str, lon: str) -> tuple[bool, str]:
        try:
            lat_value = float(str(lat).strip())
            lon_value = float(str(lon).strip())
        except ValueError:
            return False, "Location must be numeric."

        if lat_value < -90 or lat_value > 90:
            return False, "Latitude must be between -90 and 90."
        if lon_value < -180 or lon_value > 180:
            return False, "Longitude must be between -180 and 180."

        try:
            updated = save_system_location(lat=lat_value, lon=lon_value)
            self._config.system.location.lat = updated.system.location.lat
            self._config.system.location.lon = updated.system.location.lon
            return True, "Location saved. Applies on next app launch."
        except Exception as exc:
            return False, f"Failed to save location: {exc}"

    def _save_countdown_overrides(
        self,
        event_name: str,
        target_date: str,
        target_time: str,
        refresh_seconds: str,
    ) -> tuple[bool, str]:
        name = str(event_name).strip()
        if not name:
            return False, "Event name cannot be empty."

        date_text = str(target_date).strip()
        time_text = str(target_time).strip()

        try:
            date.fromisoformat(date_text)
        except Exception:
            return False, "Target date must be YYYY-MM-DD."

        try:
            dt_time.fromisoformat(time_text)
        except Exception:
            return False, "Target time must be HH:MM:SS."

        try:
            refresh_value = float(str(refresh_seconds).strip())
        except ValueError:
            return False, "Refresh seconds must be numeric."
        if refresh_value <= 0:
            return False, "Refresh seconds must be greater than 0."

        try:
            set_app_overrides(
                "countdown_to_event",
                {
                    "event_name": name,
                    "target_date": date_text,
                    "target_time": time_text,
                    "refresh_seconds": refresh_value,
                },
            )
            return True, "Countdown config saved. Applies on next app launch."
        except Exception as exc:
            return False, f"Failed to save app config: {exc}"

    def _reset_countdown_overrides(self) -> tuple[bool, str]:
        try:
            clear_app_overrides("countdown_to_event")
            return True, "Countdown config reset to manifest defaults."
        except Exception as exc:
            return False, f"Failed to reset app config: {exc}"

    def _save_secret_value(self, key: str, value: str) -> tuple[bool, str]:
        name = str(key).strip()
        if not name:
            return False, "Secret key cannot be empty."
        if not value:
            return False, "Secret value cannot be empty."
        try:
            self._secrets.set(name, value)
            return True, f"Saved secret: {name}"
        except Exception as exc:
            return False, f"Failed to save secret: {exc}"

    def _delete_secret_value(self, key: str) -> tuple[bool, str]:
        name = str(key).strip()
        if not name:
            return False, "Secret key cannot be empty."
        try:
            deleted = self._secrets.delete(name)
            if not deleted:
                return False, f"Secret not found: {name}"
            return True, f"Deleted secret: {name}"
        except Exception as exc:
            return False, f"Failed to delete secret: {exc}"

    def _build_app_management_card(self) -> None:
        with ui.card().classes("w-full").style("background: #2a2a2a;"):
            ui.label("App Management").style(
                "font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 8px;"
            )
            ui.label("Reassign switch numbers and edit manifest config.").style(
                "color: #888888; font-size: 13px; margin-bottom: 8px;"
            )

            manifests = self._app_manager.get_all_manifests()
            switch_map = self._app_manager.get_switch_map()
            app_options = self._sorted_app_names(manifests, switch_map)
            if not app_options:
                ui.label("No apps discovered.").style("color: #888888;")
                return

            app_select = ui.select(options=app_options, label="App").classes("w-full")
            current_switch_label = ui.label("Current switch: —").style("color: #aaaaaa; font-size: 12px;")
            switch_select = ui.select(options=[], label="Switch number (available)").classes("w-full")

            manifest_area = ui.textarea(label="Manifest (read-only)").props("readonly autogrow").classes("w-full")
            config_area = ui.textarea(label="Manifest config (JSON object)").props("autogrow").classes("w-full")

            def _refresh_manifest_views(selected: str) -> None:
                ok, manifest_text, config_text, message = self._get_manifest_views(selected)
                manifest_area.set_value(manifest_text)
                config_area.set_value(config_text)
                if message:
                    ui.notify(message, color="positive" if ok else "negative")

                current_switch_map = self._app_manager.get_switch_map()
                current = self._first_switch_for_app(selected, current_switch_map)
                available = self._get_unassigned_switches(selected, current_switch_map)
                options = [str(v) for v in available]
                switch_select.set_options(options)

                if current is None:
                    current_switch_label.set_text("Current switch: —")
                    switch_select.set_value(options[0] if options else None)
                else:
                    current_switch_label.set_text(f"Current switch: {current}")
                    switch_select.set_value(str(current))

            app_select.set_value(app_options[0])
            _refresh_manifest_views(app_options[0])

            def _on_select(e) -> None:
                selected = str(e.value or "").strip()
                if selected:
                    _refresh_manifest_views(selected)

            app_select.on("update:model-value", _on_select)

            with ui.row().classes("gap-2"):
                def _assign_switch() -> None:
                    ok, message = self._assign_app_switch(
                        app_name=str(app_select.value or ""),
                        switch_value_text=str(switch_select.value or ""),
                    )
                    if ok:
                        _refresh_manifest_views(str(app_select.value or ""))
                    ui.notify(message, color="positive" if ok else "negative")

                def _reload_manifest() -> None:
                    _refresh_manifest_views(str(app_select.value or ""))

                ui.button("Assign Switch Number", on_click=_assign_switch, icon="pin").props("color=primary")
                ui.button("Reload Manifest", on_click=_reload_manifest, icon="refresh").props("flat color=primary")

            with ui.row().classes("gap-2"):
                def _save_manifest_config_click() -> None:
                    ok, message = self._save_manifest_config(
                        app_name=str(app_select.value or ""),
                        config_text=str(config_area.value or "{}"),
                    )
                    if ok:
                        _refresh_manifest_views(str(app_select.value or ""))
                    ui.notify(message, color="positive" if ok else "negative")

                ui.button("Save Manifest Config", on_click=_save_manifest_config_click, icon="save").props(
                    "color=primary"
                )

    def _sorted_app_names(
        self,
        manifests: dict[str, object],
        switch_map: dict[int, str],
    ) -> list[str]:
        reverse: dict[str, list[int]] = {}
        for sw, app in switch_map.items():
            reverse.setdefault(app, []).append(sw)
        return sorted(
            manifests.keys(),
            key=lambda app: (min(reverse.get(app, [999])), app),
        )

    def _first_switch_for_app(self, app_name: str, switch_map: dict[int, str]) -> int | None:
        values = [sw for sw, name in switch_map.items() if name == app_name]
        if not values:
            return None
        return min(values)

    def _get_unassigned_switches(self, app_name: str, switch_map: dict[int, str]) -> list[int]:
        assigned_to_others = {sw for sw, name in switch_map.items() if name != app_name}
        return [value for value in range(256) if value not in assigned_to_others]

    def _mappings_file_path(self) -> Path:
        p = getattr(self._app_manager, "_mappings_path", None)
        if not isinstance(p, Path):
            raise RuntimeError("App manager mappings path not available")
        return p

    def _atomic_write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=str(path.parent))
        try:
            with open(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
            Path(tmp_name).replace(path)
        finally:
            tmp_path = Path(tmp_name)
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def _assign_app_switch(self, app_name: str, switch_value_text: str) -> tuple[bool, str]:
        name = app_name.strip()
        if not name:
            return False, "Select an app first."

        try:
            switch_value = int(switch_value_text.strip())
        except ValueError:
            return False, "Switch number must be an integer."

        if switch_value < 0 or switch_value > 255:
            return False, "Switch number must be between 0 and 255."

        path = self._mappings_file_path()
        raw = json.loads(path.read_text(encoding="utf-8"))
        wrapped = isinstance(raw, dict) and isinstance(raw.get("app_mappings"), dict)
        mappings = dict(raw.get("app_mappings", {})) if wrapped else dict(raw)

        existing = mappings.get(str(switch_value))
        if existing and existing != name:
            return False, f"Switch {switch_value} is already assigned to '{existing}'."

        for key, value in list(mappings.items()):
            if value == name:
                del mappings[key]
        mappings[str(switch_value)] = name

        ordered = dict(sorted(mappings.items(), key=lambda item: int(item[0])))
        payload = dict(raw)
        if wrapped:
            payload["app_mappings"] = ordered
        else:
            payload = ordered

        self._atomic_write_json(path, payload)
        self._app_manager.scan_apps()
        return True, f"Assigned '{name}' to switch {switch_value}."

    def _get_manifest_views(self, app_name: str) -> tuple[bool, str, str, str]:
        name = app_name.strip()
        if not name:
            return False, "", "{}", "Select an app first."

        app_dir = self._app_manager.get_app_dir(name)
        if app_dir is None:
            return False, "", "{}", f"App directory not found for '{name}'."
        manifest_path = app_dir / "manifest.json"
        if not manifest_path.is_file():
            return False, "", "{}", f"Manifest not found for '{name}'."

        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        config = raw.get("config", {})
        if not isinstance(config, dict):
            config = {}
        return (
            True,
            json.dumps(raw, indent=2),
            json.dumps(config, indent=2),
            "",
        )

    def _save_manifest_config(self, app_name: str, config_text: str) -> tuple[bool, str]:
        name = app_name.strip()
        if not name:
            return False, "Select an app first."

        app_dir = self._app_manager.get_app_dir(name)
        if app_dir is None:
            return False, f"App directory not found for '{name}'."
        manifest_path = app_dir / "manifest.json"
        if not manifest_path.is_file():
            return False, f"Manifest not found for '{name}'."

        try:
            config_obj = json.loads(config_text)
        except json.JSONDecodeError as exc:
            return False, f"Config JSON is invalid: {exc}"

        if not isinstance(config_obj, dict):
            return False, "Config must be a JSON object."

        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw["config"] = config_obj
        self._atomic_write_json(manifest_path, raw)
        self._app_manager.scan_apps()
        return True, f"Saved config for '{name}'."

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
            full_switch_map = self._app_manager.get_switch_map()
            for app_name in self._sorted_app_names(manifests, full_switch_map):
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
            ui.label("Keys can be added, updated, or deleted here. Values are hidden.").style(
                "color: #888888; font-size: 13px; margin-bottom: 8px;"
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

            ui.separator().style("background: #444444; margin-top: 10px;")
            ui.label("Edit Secret").style(
                "font-size: 16px; font-weight: bold; color: #ffffff; margin-top: 8px;"
            )

            select_key = ui.select(
                options=sorted(all_keys.keys()),
                label="Known key (optional)",
            ).classes("w-full")
            key_input = ui.input("Secret key", placeholder="BOSS_APP_EXAMPLE_API_KEY").classes("w-full")
            value_input = ui.input(
                "Secret value",
                password=True,
                password_toggle_button=True,
            ).classes("w-full")

            def _sync_key(e) -> None:
                if e.value:
                    key_input.set_value(str(e.value))

            select_key.on("update:model-value", _sync_key)

            with ui.row().classes("gap-2"):
                def _save_secret() -> None:
                    ok, message = self._save_secret_value(
                        str(key_input.value or ""),
                        str(value_input.value or ""),
                    )
                    if ok:
                        value_input.set_value("")
                    ui.notify(message, color="positive" if ok else "negative")

                def _delete_secret() -> None:
                    ok, message = self._delete_secret_value(str(key_input.value or ""))
                    ui.notify(message, color="positive" if ok else "negative")

                ui.button("Save / Update Secret", on_click=_save_secret, icon="save").props("color=primary")
                ui.button("Delete Secret", on_click=_delete_secret, icon="delete").props("flat color=warning")

    # ------------------------------------------------------------------
    # Git update card
    # ------------------------------------------------------------------

    def _build_git_update_card(self) -> None:
        with ui.card().classes("w-full").style("background: #2a2a2a;"):
            ui.label("Software Update").style(
                "font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 8px;"
            )
            ui.label("Recommended flow: check first, then apply. Apply uses fast-forward only.").style(
                "color: #888888; font-size: 13px; margin-bottom: 8px;"
            )

            repo_dir = self._repo_root()
            ui.label(f"Repository: {repo_dir}").style(
                "color: #888888; font-size: 13px; margin-bottom: 4px;"
            )

            output_area = ui.log(max_lines=50).classes("w-full").style(
                "height: 150px; background: #111111; color: #cccccc; "
                "font-family: 'Courier New', monospace; font-size: 12px;"
            )
            output_area.push("Step 1: Check updates. Step 2: Apply update if ready.")

            with ui.row().classes("gap-2"):
                def _check_updates() -> None:
                    output_area.clear()
                    ok, lines = self._check_for_updates()
                    for line in lines:
                        output_area.push(line)
                    ui.notify(
                        "Update check complete" if ok else "Update check failed",
                        color="positive" if ok else "negative",
                    )

                def _apply_updates() -> None:
                    output_area.clear()
                    ok, lines = self._apply_git_update()
                    for line in lines:
                        output_area.push(line)
                    ui.notify(
                        "Update applied" if ok else "Update failed",
                        color="positive" if ok else "negative",
                    )

                ui.button("1) Check Updates", on_click=_check_updates, icon="refresh").props(
                    "flat color=primary"
                )
                ui.button("2) Apply Update", on_click=_apply_updates, icon="download").props(
                    "color=warning"
                )

    def _repo_root(self) -> Path:
        deployed = Path("/opt/boss")
        if deployed.is_dir():
            return deployed
        return Path(__file__).resolve().parents[3]

    def _run_git_command(self, args: list[str], timeout: int = 30) -> tuple[int, str, str]:
        result = subprocess.run(
            ["git", *args],
            cwd=str(self._repo_root()),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()

    def _check_for_updates(self) -> tuple[bool, list[str]]:
        lines = ["Checking for updates …"]
        code, out, err = self._run_git_command(["fetch", "--all", "--prune"], timeout=60)
        if out:
            lines.extend(out.splitlines())
        if err:
            lines.extend([f"stderr: {line}" for line in err.splitlines()])
        if code != 0:
            lines.append(f"Exit code: {code}")
            return False, lines

        code, out, err = self._run_git_command(["status", "-sb"]) 
        if out:
            lines.extend(out.splitlines())
        if err:
            lines.extend([f"stderr: {line}" for line in err.splitlines()])

        code_log, log_out, log_err = self._run_git_command(["log", "--oneline", "HEAD..@{u}"])
        if log_out:
            lines.append("Commits available upstream:")
            lines.extend(log_out.splitlines()[:20])
        elif code_log == 0:
            lines.append("Already up to date with upstream.")

        if log_err and "no upstream configured" in log_err.lower():
            lines.append("No upstream branch configured.")
        elif log_err:
            lines.extend([f"stderr: {line}" for line in log_err.splitlines()])

        return True, lines

    def _apply_git_update(self) -> tuple[bool, list[str]]:
        lines = ["Applying update with fast-forward only …"]
        code, out, err = self._run_git_command(["pull", "--ff-only"], timeout=90)
        if out:
            lines.extend(out.splitlines())
        if err:
            lines.extend([f"stderr: {line}" for line in err.splitlines()])
        lines.append(f"Exit code: {code}")
        if code == 0:
            lines.append("Update complete. Restart BOSS service if required.")
            return True, lines
        return False, lines

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

