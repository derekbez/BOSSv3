# Hardware Abstraction & Parity

## Hardware Components

| Component | Interface | GPIO Impl | Mock Impl |
|-----------|-----------|-----------|-----------|
| Color buttons (R/Y/G/B) | `ButtonInterface` | gpiozero `Button` | In-memory + `simulate_press()` |
| Go button | `GoButtonInterface` | gpiozero `Button` | In-memory + `simulate_press()` |
| Color LEDs (R/Y/G/B) | `LedInterface` | gpiozero `LED` | In-memory state |
| 8-bit switches | `SwitchInterface` | 74HC151 MUX via GPIO | In-memory value |
| 7-segment display | `DisplayInterface` | TM1637 driver | In-memory value |
| Screen | `ScreenInterface` | NiceGUI (same as dev) | NiceGUI or in-memory |
| Speaker | `SpeakerInterface` | Audio playback | Log-only stub |

## Two Backends Only

- **`gpio`** — real Raspberry Pi hardware (auto-detected on Linux + ARM)
- **`mock`** — in-memory for testing; has `simulate_*()` methods

There is NO `webui` backend. The browser UI (NiceGUI) is the production screen on all
platforms. The dev simulation panel is a UI concern, not a hardware backend.

## LED/Button Parity (Critical)

**Buttons are only active when their LED is on.** This is enforced at the
`HardwareEventBridge` level:

```python
def _on_button_pressed(self, color: str):
    if self._led_states.get(color, False):
        self.event_bus.publish("input.button.pressed", {"button": color})
    # else: silently ignored
```

All apps MUST:

1. Turn on LEDs for buttons they will handle
2. Turn off LEDs in their `finally` block
3. Never assume a button press without checking LED state

## ScreenInterface (Simplified)

```python
class ScreenInterface(ABC):
    def display_text(self, text: str, **kwargs) -> None: ...
    def display_html(self, html: str) -> None: ...
    def display_image(self, image_path: str) -> None: ...
    def display_markdown(self, markdown: str) -> None: ...
    def clear(self) -> None: ...
```

No `wrap`, `wrap_width`, `font_size`, `color`, `background`, `align` in the ABC.
Style is handled by the NiceGUI implementation via `**kwargs` on `display_text()`.

## Switch Monitoring

- ~20Hz polling in a background thread (GPIO, 50ms sleep) or event-driven (mock)
- Switch value is 0–255 (8-bit binary from toggle switches)
- Value displayed on TM1637 7-segment display (system-controlled, not app-controlled)

## Dev Simulation Panel

On non-Pi platforms, `ui/dev_panel.py` renders NiceGUI controls:

- Virtual buttons → publish `input.button.pressed` events
- Switch slider → publish `input.switch.changed` events
- LED indicators → update on `output.led.state_changed` events
- 7-seg readout → update on `output.display.updated` events

This replaces the v2 WebUI hardware backend entirely.
