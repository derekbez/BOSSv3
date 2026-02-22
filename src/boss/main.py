"""BOSS v3 — Application entry point (NiceGUI composition root).

Wires together: Config → EventBus → HardwareFactory → SystemManager → UI.
NiceGUI owns the event loop; ``app.on_startup`` / ``app.on_shutdown``
handle lifecycle.
"""

from __future__ import annotations

import logging as _logging
from pathlib import Path

from nicegui import app, ui

from boss.config.config_manager import load_config
from boss.config.secrets_manager import SecretsManager
from boss.core.event_bus import EventBus
from boss.hardware.factory import create_hardware_factory
from boss.logging.logger import setup_logging

_log = _logging.getLogger(__name__)


def main() -> None:
    """Synchronous entry point — bootstraps and starts NiceGUI."""

    setup_logging()
    _log.info("Starting BOSS v3")

    # 1. Load configuration
    config = load_config()
    secrets = SecretsManager()

    # 2. Create event bus
    bus = EventBus()

    # 3. Create hardware factory (mock on dev, GPIO on Pi)
    factory = create_hardware_factory(config)

    # 4. Inject NiceGUIScreen into whichever factory was created.
    #    Both MockHardwareFactory and GPIOHardwareFactory support set_screen().
    from boss.hardware.mock.mock_factory import MockHardwareFactory
    from boss.ui.screen import NiceGUIScreen

    nicegui_screen = NiceGUIScreen()

    # Both mock and GPIO factories support set_screen().
    factory.set_screen(nicegui_screen)

    # 5. Resolve paths
    pkg_dir = Path(__file__).resolve().parent
    apps_dir = pkg_dir / "apps"
    mappings_path = pkg_dir / "config" / "app_mappings.json"

    # 6. Create SystemManager (imported here to avoid circular refs)
    from boss.core.system_manager import SystemManager

    system = SystemManager(
        config=config,
        event_bus=bus,
        hardware_factory=factory,
        apps_dir=apps_dir,
        mappings_path=mappings_path,
        secrets=secrets,
    )

    # 7. Set up UI layout
    from boss.ui.layout import BossLayout

    layout = BossLayout(screen=nicegui_screen, event_bus=bus, config=config)
    layout.setup_page()

    # 8. Set up admin page (/admin and /admin/wifi routes)
    from boss.ui.admin_page import AdminPage

    # Admin page needs app_manager and app_runner which are created in
    # SystemManager.start(). We wire up a deferred setup via on_startup.

    admin_page: AdminPage | None = None

    # 9. Set up dev panel (mock hardware only)
    if isinstance(factory, MockHardwareFactory):
        from boss.ui.dev_panel import DevPanel

        dev_panel = DevPanel(factory=factory, event_bus=bus)

        @ui.page("/")
        def _index_with_dev():
            layout._build_page()
            dev_panel.build()

    # 10. Wire lifecycle hooks
    async def on_startup() -> None:
        _log.info("NiceGUI startup — starting BOSS system")
        await system.start()

        # Now that SystemManager.start() has been called, wire admin page
        nonlocal admin_page
        admin_page = AdminPage(
            event_bus=bus,
            config=config,
            app_manager=system.app_manager,
            app_runner=system.app_runner,
            secrets=secrets,
        )
        admin_page.setup_page()

        _log.info("BOSS v3 running on http://localhost:%d", config.system.webui_port)

    async def on_shutdown() -> None:
        _log.info("NiceGUI shutdown — stopping BOSS system")
        await system.shutdown(reason="nicegui shutdown")
        _log.info("BOSS v3 stopped")

    app.on_startup(on_startup)
    app.on_shutdown(on_shutdown)

    # 11. Launch NiceGUI (blocks forever)
    ui.run(
        port=config.system.webui_port,
        title="BOSS v3",
        reload=False,
        show=False,
    )


if __name__ == "__main__":
    main()
