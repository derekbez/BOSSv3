"""Integration test — end-to-end event flow through the real composition.

Boots EventBus + AppManager + AppRunner + AppLauncher with mock hardware,
fires a GO_BUTTON_PRESSED event, and asserts the app starts, renders on
screen, and publishes the expected lifecycle events.
"""

from __future__ import annotations

import asyncio
import json
import textwrap
from pathlib import Path

import pytest

from boss.config.secrets_manager import SecretsManager
from boss.core import events
from boss.core.app_launcher import AppLauncher
from boss.core.app_manager import AppManager
from boss.core.app_runner import AppRunner
from boss.core.event_bus import EventBus
from boss.core.hardware_event_bridge import HardwareEventBridge
from boss.core.models.config import BossConfig
from boss.core.models.event import Event
from boss.hardware.mock.mock_factory import MockHardwareFactory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_test_app(tmp_path: Path, name: str, code: str) -> None:
    """Write a minimal app with manifest into a temp directory."""
    app_dir = tmp_path / name
    app_dir.mkdir()
    (app_dir / "main.py").write_text(code, encoding="utf-8")
    (app_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": name.replace("_", " ").title(),
                "description": f"Test app {name}",
                "version": "1.0.0",
                "timeout_seconds": 30,
            }
        ),
        encoding="utf-8",
    )


def _create_mappings(tmp_path: Path, mappings: dict[str, str]) -> Path:
    """Write an app_mappings.json file and return its path."""
    p = tmp_path / "app_mappings.json"
    p.write_text(json.dumps(mappings), encoding="utf-8")
    return p


async def _wait_for_async(
    condition,
    timeout: float = 5.0,
    interval: float = 0.05,
) -> None:
    """Poll *condition* until truthy, or raise TimeoutError."""
    elapsed = 0.0
    while not condition():
        if elapsed >= timeout:
            raise TimeoutError(f"Condition not met within {timeout}s")
        await asyncio.sleep(interval)
        elapsed += interval


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGoButtonLaunchesApp:
    """Verify the full event chain: GO press → app starts → renders → finishes."""

    @pytest.fixture
    def factory(self) -> MockHardwareFactory:
        return MockHardwareFactory()

    @pytest.fixture
    async def bus(self):
        bus = EventBus(queue_size=100)
        await bus.start()
        yield bus
        await bus.stop()

    @pytest.fixture
    def config(self) -> BossConfig:
        return BossConfig()

    @pytest.fixture
    def secrets(self) -> SecretsManager:
        return SecretsManager()

    @pytest.mark.asyncio
    async def test_go_button_runs_app_and_emits_lifecycle_events(
        self, tmp_path, factory, bus, config, secrets
    ):
        """Fire GO_BUTTON_PRESSED and verify the complete lifecycle."""

        # --- set up a tiny app that writes to screen and exits ---------
        app_code = textwrap.dedent("""\
            def run(stop_event, api):
                api.screen.display_text("integration-test-output")
        """)
        _create_test_app(tmp_path, "test_app", app_code)
        _create_mappings(tmp_path, {"42": "test_app"})

        # --- wire real components with mock hardware -------------------
        factory.switches._value = 42  # pre-set without triggering callback

        bridge = HardwareEventBridge(
            event_bus=bus,
            buttons=factory.buttons,
            go_button=factory.go_button,
            leds=factory.leds,
            switches=factory.switches,
        )

        app_mgr = AppManager(tmp_path, tmp_path / "app_mappings.json", secrets)
        app_mgr.scan_apps()

        runner = AppRunner(bus)

        screen = factory.create_screen()

        launcher = AppLauncher(
            event_bus=bus,
            app_manager=app_mgr,
            app_runner=runner,
            switches=factory.switches,
            leds=factory.leds,
            display=factory.display,
            screen=screen,
            config=config,
            secrets=secrets,
        )

        # --- collect lifecycle events ----------------------------------
        received: list[str] = []

        def _record(evt: Event):
            received.append(evt.event_type)

        bus.subscribe(events.APP_LAUNCH_REQUESTED, _record)
        bus.subscribe(events.APP_STARTED, _record)
        bus.subscribe(events.APP_FINISHED, _record)
        bus.subscribe(events.APP_ERROR, _record)

        # --- fire go-button press --------------------------------------
        await bus.publish(events.GO_BUTTON_PRESSED, {})

        # --- wait for app to finish ------------------------------------
        await _wait_for_async(
            lambda: events.APP_FINISHED in received,
            timeout=5.0,
        )

        # --- assertions ------------------------------------------------
        assert events.APP_LAUNCH_REQUESTED in received
        assert events.APP_STARTED in received
        assert events.APP_FINISHED in received

        # The app wrote to screen (then cleanup cleared it).
        # Check the call_log for the full record.
        texts = [
            args["text"]
            for method, args in screen.call_log
            if method == "display_text"
        ]
        assert "integration-test-output" in texts

    @pytest.mark.asyncio
    async def test_unmapped_switch_shows_error_on_screen(
        self, tmp_path, factory, bus, config, secrets
    ):
        """When no app is mapped to the current switch, show an error."""

        # No apps at all
        _create_mappings(tmp_path, {})

        factory.switches._value = 99

        app_mgr = AppManager(tmp_path, tmp_path / "app_mappings.json", secrets)
        app_mgr.scan_apps()

        runner = AppRunner(bus)
        screen = factory.create_screen()

        launcher = AppLauncher(
            event_bus=bus,
            app_manager=app_mgr,
            app_runner=runner,
            switches=factory.switches,
            leds=factory.leds,
            display=factory.display,
            screen=screen,
            config=config,
            secrets=secrets,
        )

        await bus.publish(events.GO_BUTTON_PRESSED, {})

        # Give time for the event to be dispatched
        await _wait_for_async(
            lambda: screen.last_text is not None,
            timeout=3.0,
        )

        assert "No app" in (screen.last_text or "")
        assert "99" in (screen.last_text or "")

    @pytest.mark.asyncio
    async def test_app_error_emits_error_event(
        self, tmp_path, factory, bus, config, secrets
    ):
        """An app that raises should emit APP_ERROR."""

        app_code = textwrap.dedent("""\
            def run(stop_event, api):
                raise RuntimeError("boom")
        """)
        _create_test_app(tmp_path, "bad_app", app_code)
        _create_mappings(tmp_path, {"7": "bad_app"})

        factory.switches._value = 7

        app_mgr = AppManager(tmp_path, tmp_path / "app_mappings.json", secrets)
        app_mgr.scan_apps()

        runner = AppRunner(bus)
        screen = factory.create_screen()

        launcher = AppLauncher(
            event_bus=bus,
            app_manager=app_mgr,
            app_runner=runner,
            switches=factory.switches,
            leds=factory.leds,
            display=factory.display,
            screen=screen,
            config=config,
            secrets=secrets,
        )

        received: list[str] = []

        def _record(evt: Event):
            received.append(evt.event_type)

        bus.subscribe(events.APP_ERROR, _record)
        bus.subscribe(events.APP_FINISHED, _record)

        await bus.publish(events.GO_BUTTON_PRESSED, {})

        await _wait_for_async(
            lambda: events.APP_ERROR in received,
            timeout=5.0,
        )

        assert events.APP_ERROR in received
