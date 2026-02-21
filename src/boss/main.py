"""BOSS v3 — Application entry point."""

from __future__ import annotations

import asyncio
import signal

from boss.logging.logger import get_logger, setup_logging

logger = get_logger(__name__)


async def _run() -> None:
    """Bootstrap and run the BOSS platform."""
    from boss.config.config_manager import load_config
    from boss.config.secrets_manager import SecretsManager
    from boss.core.system_manager import SystemManager

    setup_logging()
    logger.info("Starting BOSS v3")

    config = load_config()
    secrets = SecretsManager()
    system = SystemManager(config=config, secrets=secrets)

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Received shutdown signal")
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await system.start()
    logger.info("BOSS v3 running — press Ctrl+C to stop")

    await stop.wait()

    logger.info("Shutting down BOSS v3")
    await system.shutdown()
    logger.info("BOSS v3 stopped")


def main() -> None:
    """Synchronous entry point."""
    asyncio.run(_run())


if __name__ == "__main__":
    main()
