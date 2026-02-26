"""Hardware factory — platform detection and factory creation.

Selects GPIO on Raspberry Pi, Mock on everything else (Windows, Mac, CI).
"""

from __future__ import annotations

import logging

from boss.core.interfaces.hardware import HardwareFactory
from boss.core.models.config import BossConfig

_log = logging.getLogger(__name__)


def _is_raspberry_pi() -> bool:
    """Return ``True`` if running on a Raspberry Pi."""
    try:
        with open("/sys/firmware/devicetree/base/model") as f:
            model = f.read().lower()
        return "raspberry pi" in model
    except OSError:
        return False


def create_hardware_factory(config: BossConfig) -> HardwareFactory:
    """Return the appropriate :class:`HardwareFactory` for the platform.

    * On Raspberry Pi (detected via device-tree) → ``GPIOHardwareFactory``
      (requires Phase 4; raises ``ImportError`` until implemented).
    * Everywhere else (or if ``dev_mode`` is ``True``) → ``MockHardwareFactory``.
    """
    if config.system.dev_mode or not _is_raspberry_pi():
        from boss.hardware.mock.mock_factory import MockHardwareFactory

        _log.info("Using MockHardwareFactory (dev_mode=%s, is_pi=%s)",
                   config.system.dev_mode, _is_raspberry_pi())
        return MockHardwareFactory()

    # GPIO — will be implemented in Phase 4.
    try:
        from boss.hardware.gpio.gpio_factory import GPIOHardwareFactory  # type: ignore[import-not-found]
        _log.info("Using GPIOHardwareFactory")
        return GPIOHardwareFactory(config)
    except ImportError:
        _log.warning("GPIOHardwareFactory not available — falling back to mock")
        from boss.hardware.mock.mock_factory import MockHardwareFactory
        return MockHardwareFactory()
