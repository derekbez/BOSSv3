# Event Bus & Logging

## Event Bus

Async-native event bus running on the NiceGUI/asyncio event loop.

### Publishing

```python
# From async code (event loop thread):
await event_bus.publish("input.button.pressed", {"button": "red"})

# From sync code (GPIO callback thread):
event_bus.publish_threadsafe("input.button.pressed", {"button": "red"})
```

### Subscribing

```python
sub_id = event_bus.subscribe("input.button.pressed", handler)
sub_id = event_bus.subscribe("input.button.pressed", handler, filter_dict={"button": "red"})
event_bus.unsubscribe(sub_id)
```

Handlers can be sync or async. Sync handlers are wrapped automatically.

### Error Handling

If a handler raises an exception, it is logged and **auto-unsubscribed** to prevent
repeated failures from blocking the event pipeline.

## Event Taxonomy

| Category | Event | Payload |
|----------|-------|---------|
| **Input** | `input.switch.changed` | `{old_value: int, new_value: int}` |
| | `input.button.pressed` | `{button: "red\|yellow\|green\|blue"}` |
| | `input.button.released` | `{button: "red\|yellow\|green\|blue"}` |
| | `input.go_button.pressed` | `{}` |
| **Output** | `output.led.state_changed` | `{color: str, is_on: bool}` |
| | `output.display.updated` | `{value: int\|None}` |
| | `output.screen.updated` | `{content_type: str, content: str}` |
| **System** | `system.started` | `{hardware_type: str}` |
| | `system.shutdown.requested` | `{action: str, reason: str}` |
| | `system.shutdown.initiated` | `{reason: str}` |
| **App** | `system.app.launch.requested` | `{switch_value: int}` |
| | `system.app.started` | `{app_name: str, switch_value: int}` |
| | `system.app.finished` | `{app_name: str, reason: str}` |
| | `system.app.error` | `{app_name: str, error: str}` |

### Naming Rules

- Always use canonical names from the table above
- `input.*` for physical/simulated user actions
- `output.*` for system-driven hardware changes
- `system.*` for lifecycle and orchestration

## Logging

### Setup

```python
from boss.logging import setup_logging, get_logger

setup_logging(log_level="INFO", log_dir="logs/")
logger = get_logger(__name__)
```

### ContextualLogger

Wraps standard logger with `[key=value]` context prefixes:

```python
ctx_logger = ContextualLogger(logger, app_name="weather")
ctx_logger.info("Fetching data")  # → [app_name=weather] Fetching data
```

### Levels

- **DEBUG**: Internal state, event payloads, timing
- **INFO**: App start/stop, significant state changes
- **WARNING**: Degraded operation, fallbacks
- **ERROR**: Failures that don't crash the system
- **CRITICAL**: System cannot continue
