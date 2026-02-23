"""Tests for hardware factory selection and dev_mode side effects."""

from __future__ import annotations

from boss.hardware.factory import create_hardware_factory, _is_raspberry_pi
from boss.core.models.config import BossConfig


def test_mock_factory_sets_dev_mode(monkeypatch):
    cfg = BossConfig()
    # ensure we're not pretending to be running on a Pi
    monkeypatch.setattr("boss.hardware.factory._is_raspberry_pi", lambda: False)

    factory = create_hardware_factory(cfg)
    from boss.hardware.mock.mock_factory import MockHardwareFactory

    assert isinstance(factory, MockHardwareFactory)
    assert cfg.system.dev_mode is True


def test_pi_factory_leaves_dev_mode_unchanged(monkeypatch):
    cfg = BossConfig()
    # pretend to be on a Pi and disable dev_mode
    cfg.system.dev_mode = False
    monkeypatch.setattr("boss.hardware.factory._is_raspberry_pi", lambda: True)

    # The real GPIOHardwareFactory may raise when invoked in a non-Pi test
    # environment; we don't care about the actual factory object here, only
    # that dev_mode isn't flipped by create_hardware_factory.
    try:
        _ = create_hardware_factory(cfg)
    except Exception:
        pass
    assert cfg.system.dev_mode is False
