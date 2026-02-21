# Testing Strategy

## Structure

```
tests/
  conftest.py           # Shared fixtures (event_bus, config, hardware_factory, etc.)
  helpers/
    app_scaffold.py     # create_app() for dynamic test apps
    runtime.py          # wait_for(), wait_for_app_started(), wait_for_app_finished()
  unit/
    core/               # Event bus, app manager, app runner, config, models
    hardware/           # Mock hardware, factory detection
  integration/          # Full system lifecycle, NiceGUI UI tests
```

## Fixtures

| Fixture | Scope | Provides |
|---------|-------|----------|
| `event_bus` | function | Fresh `EventBus` instance |
| `boss_config` | session | `BossConfig` from test config |
| `hardware_factory` | function | `MockHardwareFactory` |
| `app_runner` | function | `AppRunner` with mock hardware |

## Principles

- **Deterministic**: use `wait_for(condition, timeout)` not `time.sleep()`
- **Isolated**: each test gets fresh event bus and hardware
- **Fast**: no NiceGUI in unit tests; mock hardware only
- **Real integration**: use `nicegui.testing.Screen` for UI tests

## Test Helpers

```python
# Wait for a condition with timeout (from helpers/runtime.py)
await wait_for(lambda: app.status == AppStatus.RUNNING, timeout=5.0)

# Create a temporary test app (from helpers/app_scaffold.py)
app_dir = create_app("test_app", code='api.screen.display_text("hi")')
```

## Markers

```ini
# pyproject.toml [tool.pytest.ini_options]
markers =
    slow: deselect with -m "not slow"
    pi_only: requires Raspberry Pi hardware
    live_api: calls real external APIs
```

## Running Tests

```bash
pytest                          # All non-slow tests
pytest -m "not live_api"        # Skip live API calls
pytest tests/unit/              # Unit tests only
pytest --cov=boss               # With coverage
```

## Smoke Tests

Every migrated mini-app has a smoke test that:

1. Creates a `DummyAPI` (no real hardware/NiceGUI)
2. Calls `run(stop_event, api)` with a short timeout
3. Verifies it doesn't crash
4. Verifies it calls `api.screen.*` at least once
