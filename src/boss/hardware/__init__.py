"""Hardware abstraction: factory + platform backends (gpio, mock)."""

from boss.hardware.factory import create_hardware_factory

__all__ = ["create_hardware_factory"]
