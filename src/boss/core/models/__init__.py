"""Pydantic models for configuration, manifests, and hardware state."""
from boss.core.models.config import BossConfig, HardwareConfig, LocationConfig, SystemConfig
from boss.core.models.event import Event
from boss.core.models.manifest import AppManifest, migrate_manifest_v2
from boss.core.models.state import ButtonColor, LedColor

__all__ = [
    "BossConfig",
    "HardwareConfig",
    "LocationConfig",
    "SystemConfig",
    "AppManifest",
    "migrate_manifest_v2",
    "Event",
    "ButtonColor",
    "LedColor",
]
