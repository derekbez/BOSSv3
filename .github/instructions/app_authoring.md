# Mini-App Authoring & Lifecycle

## Contract

Every mini-app must provide:

```
src/boss/apps/<app_name>/
  main.py          # def run(stop_event, api) -> None
  manifest.json    # Pydantic-validated metadata
  assets/          # Optional: images, sounds, data files
```

### `run(stop_event, api)`

- `stop_event`: `threading.Event` — set when app should stop
- `api`: `AppAPI` — scoped access to screen, hardware, events, config, logging

### manifest.json (Pydantic `AppManifest`)

```json
{
  "name": "My App",
  "description": "What it does",
  "version": "1.0.0",
  "author": "Your Name",
  "entry_point": "main.py",
  "timeout_seconds": 120,
  "timeout_behavior": "return",
  "requires_network": false,
  "requires_audio": false,
  "tags": ["example"],
  "config": {
    "custom_key": "custom_value"
  }
}
```

The `config` field is a free-form dict accessible via `api.get_config_value(key, default)`.

## AppAPI Methods

### Screen

```python
api.screen.display_text("Hello", font_size=32, color="white")
api.screen.display_html("<h1>Rich HTML</h1><img src='...'/>")
api.screen.display_image("assets/photo.png")
api.screen.display_markdown("# Title\n\nBody text")
api.screen.clear()
```

### Hardware (LEDs only — display is system-controlled)

```python
api.hardware.set_led("red", True)
api.hardware.set_led("green", False)
```

### Events

```python
sub_id = api.event_bus.subscribe("input.button.pressed", handler, filter_dict={"button": "red"})
api.event_bus.unsubscribe(sub_id)
```

### Config & Assets

```python
value = api.get_config_value("refresh_seconds", default=30)
path = api.get_asset_path("data.json")
location = api.get_global_location()  # {"lat": ..., "lon": ...}
```

### Logging

```python
api.log_info("Started")
api.log_error("Something broke")
```

## Lifecycle

1. User sets switches (0–255), presses Go
2. System snapshots switch value, looks up app in `app_mappings.json`
3. `AppRunner` spawns daemon thread, calls `run(stop_event, api)`
4. App runs until `stop_event` is set (user action, timeout, or natural exit)
5. `finally` block cleans up LEDs, unsubscribes events

## Required Pattern

```python
def run(stop_event, api):
    api.log_info("Starting")
    # Light LEDs for buttons you'll use
    api.hardware.set_led("red", True)

    def on_red(event_type, payload):
        api.screen.display_text("Red pressed!")

    api.event_bus.subscribe("input.button.pressed", on_red, filter_dict={"button": "red"})

    try:
        api.screen.display_text("Press red button!")
        stop_event.wait()  # Block until stopped
    finally:
        api.hardware.set_led("red", False)
        api.log_info("Stopped")
```

## Anti-Patterns

- `def run(stop_event, api, **kwargs)` — no extra args
- `import gpiozero` — never import hardware directly
- `while True: time.sleep(1)` — use `stop_event.wait(1)`
- Forgetting `finally` cleanup — always turn off LEDs
- `os.path.join(__file__, ...)` — use `api.get_asset_path()`
