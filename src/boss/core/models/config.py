"""Configuration Pydantic models: BossConfig, HardwareConfig, SystemConfig."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LocationConfig(BaseModel):
    """Geographic location for weather / tide / astronomy apps."""

    model_config = ConfigDict(extra="forbid")

    lat: float = Field(description="Latitude in decimal degrees")
    lon: float = Field(description="Longitude in decimal degrees")


class HardwareConfig(BaseModel):
    """Pin assignments and hardware parameters.

    All pin numbers are BCM GPIO numbers.  ``switch_pins`` and ``mux_pins``
    carry the MUX wiring for the 74HC151-based 8-bit switch reader.
    """

    model_config = ConfigDict(extra="forbid")

    # 74HC151 multiplexer wiring
    switch_pins: dict[str, int] = Field(
        default_factory=dict,
        description="MUX input pins (e.g. {'d0': 17, 'd1': 27, …})",
    )
    mux_pins: dict[str, int] = Field(
        default_factory=dict,
        description="MUX select / enable pins (e.g. {'s0': 5, 's1': 6, 's2': 13, 'en': 19})",
    )

    # Colour buttons & LEDs
    button_pins: dict[str, int] = Field(
        default_factory=lambda: {"red": 0, "yellow": 0, "green": 0, "blue": 0},
        description="GPIO pin per colour button",
    )
    go_button_pin: int = Field(default=0, description="GPIO pin for the Go button")
    led_pins: dict[str, int] = Field(
        default_factory=lambda: {"red": 0, "yellow": 0, "green": 0, "blue": 0},
        description="GPIO pin per colour LED",
    )

    # TM1637 7-segment display
    display_clk_pin: int = Field(default=0, description="TM1637 CLK pin")
    display_dio_pin: int = Field(default=0, description="TM1637 DIO pin")

    # Screen
    screen_width: int = Field(default=1024, description="Kiosk screen width in px")
    screen_height: int = Field(default=600, description="Kiosk screen height in px")

    # Audio
    audio_enabled: bool = Field(default=True, description="Enable speaker output")


class SystemConfig(BaseModel):
    """Non-hardware runtime settings."""

    model_config = ConfigDict(extra="forbid")

    default_timeout_seconds: int = Field(
        default=900, description="App timeout when manifest doesn't specify one"
    )
    log_level: str = Field(default="INFO", description="Root log level")
    log_dir: str = Field(default="logs", description="Directory for rotating log files")
    event_bus_queue_size: int = Field(default=1000, description="Max queued events")
    webui_port: int = Field(default=8080, description="NiceGUI listen port")
    location: LocationConfig = Field(
        default_factory=lambda: LocationConfig(lat=51.5074, lon=-0.1278),
        description="Default geographic location (London)",
    )
    dev_mode: bool = Field(default=False, description="Enable dev panel (auto-set on non-Pi)")
    test_mode: bool = Field(default=False, description="Running under pytest")


class BossConfig(BaseModel):
    """Top-level configuration loaded from ``boss_config.json``."""

    model_config = ConfigDict(extra="forbid")

    hardware: HardwareConfig = Field(default_factory=HardwareConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)
