# Configuration & Secrets

## Config File: `src/boss/config/boss_config.json`

```json
{
  "hardware": {
    "switch_pins": { ... },
    "mux_pins": { ... },
    "button_pins": { "red": 17, "yellow": 27, "green": 22, "blue": 23 },
    "go_button_pin": 24,
    "led_pins": { "red": 5, "yellow": 6, "green": 13, "blue": 19 },
    "display_clk_pin": 20,
    "display_dio_pin": 21,
    "screen_width": 1024,
    "screen_height": 600,
    "audio_enabled": false
  },
  "system": {
    "default_timeout_seconds": 900,
    "log_level": "INFO",
    "log_dir": "logs",
    "event_bus_queue_size": 1000,
    "webui_port": 8080,
    "location": { "lat": 51.5074, "lon": -0.1278 }
  }
}
```

## Config Loading

`config_manager.get_effective_config()`:

1. Load JSON file
2. Apply environment overrides (`BOSS_LOG_LEVEL`, `BOSS_DEV_MODE`, etc.)
3. Validate via Pydantic `BossConfig` model
4. Return typed config object

## Environment Overrides

| Variable | Effect |
|----------|--------|
| `BOSS_LOG_LEVEL` | Override log level |
| `BOSS_DEV_MODE=1` | Enable dev features |
| `BOSS_TEST_MODE=1` | Force mock hardware |

## Secrets

`secrets_manager.py` provides a lazy, thread-safe singleton:

- **Precedence**: process env > secrets file > default
- **File search**: `BOSS_SECRETS_FILE` env → `secrets/secrets.env` → `/etc/boss/secrets.env`
- **Never** overrides real environment variables
- **Never** committed to git (`secrets/secrets.env` is gitignored)

### Usage

```python
from boss.config import secrets
api_key = secrets.get("WEATHER_API_KEY", default="")
```

### Template

`secrets/secrets.sample.env` documents all expected keys. Copy to `secrets.env` and fill in.

## App Mappings: `src/boss/config/app_mappings.json`

```json
{
  "app_mappings": {
    "0": "list_all_apps",
    "1": "hello_world",
    "255": "admin_shutdown"
  }
}
```

Maps switch values (0–255) to app directory names in `src/boss/apps/`.
