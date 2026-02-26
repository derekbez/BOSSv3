# B.O.S.S. v3 — Epic Tracker

> Rewrite of B.O.S.S. as a NiceGUI application with Pi OS Desktop kiosk mode.
> Reference: `.github/prompts/plan-bossV3NiceguiRewrite.prompt.md`

---

## Phase 0 — Foundation & Project Setup

- [x] **0.1** Create `BOSSv3/` project root with `src/boss/` layout
- [x] **0.2** Create `pyproject.toml` with all dependencies (core, `[pi]`, `[dev]`)
- [x] **0.3** Scaffold directory structure (core, hardware, ui, apps, config, logging, tests)
- [x] **0.4** Create `__init__.py` files for all packages
- [x] **0.5** Create `.gitignore`, `README.md`
- [x] **0.6** Create venv, install deps (`pip install -e ".[dev]"`)
- [x] **0.7** Verify `python -c "import boss"` works
- [x] **0.8** Set up Copilot instructions (`.github/instructions/`, `.github/copilot-instructions.md`)

**Acceptance:** `pip install -e ".[dev]"` succeeds, `import boss` works, `pytest` runs (0 tests collected is fine).

---

## Phase 1 — Core Rewrite

- [x] **1.1** Pydantic models: `BossConfig`, `HardwareConfig`, `SystemConfig`
  - Loads from `boss_config.json`, env overrides, validation
  - File: `core/models/config.py` — `LocationConfig`, `HardwareConfig`, `SystemConfig`, `BossConfig`
  - All use `extra="forbid"`, `dev_mode`/`test_mode` on `SystemConfig`
- [x] **1.2** Pydantic models: `AppManifest` with explicit `config: dict[str, Any] = {}`
  - Fixes v2 config-drop bug; legacy manifest migration
  - File: `core/models/manifest.py` — includes `required_env: list[str]`, `migrate_manifest_v2()`
- [x] **1.3** Pydantic models: `HardwareState`, `LedColor`, `ButtonColor`, `AppStatus`, `Event`
  - Files: `core/models/state.py`, `core/models/event.py`
  - `AppStatus` enum: IDLE, LAUNCHING, RUNNING, FINISHED, ERROR, TIMED_OUT
- [x] **1.4** Hardware ABCs: `ButtonInterface`, `GoButtonInterface`, `LedInterface`, `SwitchInterface`, `DisplayInterface`, `ScreenInterface`, `SpeakerInterface`, `HardwareFactory`
  - File: `core/interfaces/hardware.py`
  - Clean ScreenInterface: `display_text()`, `display_html()`, `display_image()`, `display_markdown()`, `clear()`
  - No `wrap`/`wrap_width` on interface — that's the UI layer's job
  - `SpeakerInterface` minimal placeholder (deferred to Phase 4)
- [x] **1.5** Config manager: load JSON → apply env overrides → validate → return `BossConfig`
  - File: `config/config_manager.py` — `load_config()`
  - Env overrides: `BOSS_LOG_LEVEL`, `BOSS_DEV_MODE`, `BOSS_TEST_MODE`, `BOSS_WEBUI_PORT`
- [x] **1.6** Secrets manager: thread-safe lazy loader, env > file > default
  - File: `config/secrets_manager.py` — `SecretsManager.get(key, default)`
  - Thread-safe via double-checked locking; `KEY=VALUE` file format
- [x] **1.7** Async event bus
  - File: `core/event_bus.py` — `EventBus` class
  - `asyncio.Queue`-based, handler dispatch on event loop
  - `publish_threadsafe()` for GPIO callback threads
  - `subscribe(event_type, handler, filter_dict=None)` — AND-matched filter
  - Auto-unsubscribe on handler error; bounded queue with drop-oldest overflow
  - Event constants: `core/events.py` (14 event types)
  - Unit tests for subscribe/publish/filter/threadsafe/error-removal/overflow
- [x] **1.8** App manager: scan `apps/` dirs, load manifests, bind to `app_mappings.json`, validate `required_env`
  - File: `core/app_manager.py` — `AppManager` class
- [x] **1.9** App runner: daemon thread per app, cooperative cancellation, timeout monitor, lifecycle events
  - File: `core/app_runner.py` — `AppRunner` class; one app at a time
- [x] **1.10** AppLauncher: Go-button → snapshot switch → transition feedback → launch app → post-app cleanup
  - File: `core/app_launcher.py` — subscribes to `input.go_button.pressed`
- [x] **1.11** HardwareEventBridge: wire hardware callbacks → event bus (LED gating for buttons)
  - File: `core/hardware_event_bridge.py` — tracks LED states, gates button presses
- [x] **1.12** SystemManager: startup + shutdown orchestration only (~100 lines)
  - File: `core/system_manager.py` — `start()` / `shutdown()` lifecycle
- [x] **1.13** AppAPI: scoped event bus, screen API, hardware API, config access, logging
  - File: `core/app_api.py` — `AppAPI`, `_ScopedEventBus`, `_HardwareAPI`
  - `get_app_config()` returns manifest `config`; `get_config_value()` with defaults
  - `get_global_location()` resolution; `get_app_path()`, `get_asset_path()`
  - Scoped event bus auto-unsubscribes on cleanup
- [x] **1.14** Logging: `setup_logging()`, `ContextualLogger`, rotating file handler
  - File: `log_config/logger.py` — no longer shadows stdlib `logging`
  - RotatingFileHandler: 5 MB max, 3 backups
- [x] **1.15** Unit tests for all Phase 1 modules (60 tests)
  - `test_config_models.py`, `test_manifest.py`, `test_event_bus.py`
  - `test_config_manager.py`, `test_secrets_manager.py`
  - `test_app_manager.py`, `test_app_runner.py`, `test_app_api.py`
  - Test helpers: `helpers/runtime.py` (`wait_for`), `helpers/app_scaffold.py` (`create_app`)

**Acceptance:** All core modules importable, unit tests green, event bus handles async + threadsafe publish, config round-trips correctly, manifest `config` field preserved.

---

## Phase 2 — NiceGUI UI Layer

- [x] **2.1** `ui/screen.py` — `NiceGUIScreen` implementing `ScreenInterface`
  - File: `ui/screen.py` — thread-safe via `run_coroutine_threadsafe`
  - `display_text()` → renders styled `ui.html` with `_escape_html`
  - `display_html()` → renders arbitrary HTML
  - `display_image()` → renders `ui.image` (real image rendering)
  - `display_markdown()` → renders `ui.markdown`
  - `clear()` → clears container
  - `bind_container()` captures NiceGUI element + event loop
  - `_SCREEN_STYLE`: 800×480 / 5:3 aspect, black bg, monospace
- [x] **2.2** `ui/layout.py` — main page with `@ui.page('/')`
  - File: `ui/layout.py` — `BossLayout` class
  - Dark theme via `ui.dark_mode().enable()`
  - Status bar: switch value (decimal + binary), active app name, system state
  - App screen container with 5:3 aspect ratio, border, dark background
  - Event subscriptions: SWITCH_CHANGED, APP_STARTED, APP_FINISHED, APP_ERROR, SYSTEM_STARTED
- [x] **2.3** `ui/dev_panel.py` — dev-mode hardware simulation
  - File: `ui/dev_panel.py` — `DevPanel` class
  - Virtual buttons (red, yellow, green, blue) routed through `MockButtons.simulate_press()`
  - Go button routed through `MockGoButton.simulate_press()`
  - Switch slider (0–255) with binary display, routed through `MockSwitches.simulate_change()`
  - LED indicators with colour glow effect on/off
  - 7-segment display readout (green monospace, text-shadow glow)
  - Keyboard shortcuts: 1-4 (buttons), Space (Go), Up/Down (switch), R (reset), M (max)
  - All actions route through mock hardware objects — full LED-gating fidelity
  - Event subscriptions: LED_STATE_CHANGED, DISPLAY_UPDATED, SWITCH_CHANGED
  - Collapsible `ui.expansion` panel, default opened
- [x] **2.4** `main.py` — NiceGUI composition root
  - File: `main.py` — `main()` function
  - Config → EventBus → HardwareFactory → NiceGUIScreen → SystemManager → Layout → DevPanel
  - `app.on_startup` starts SystemManager, `app.on_shutdown` shuts it down
  - `ui.run()` blocks main thread (port from config, no reload, no auto-show)
  - Dev mode: overrides `@ui.page('/')` to include both layout + dev panel
- [x] **2.5** Mock hardware backend (`hardware/mock/`)
  - `mock_screen.py` — `InMemoryScreen`: stores last_text/html/image/markdown, cleared flag, call_log
  - `mock_hardware.py` — `MockButtons`, `MockGoButton`, `MockLeds`, `MockSwitches`, `MockDisplay`, `MockSpeaker`
  - All with `simulate_*()` helpers for dev panel and tests
  - `MockSwitches` clamps 0–255, skips callback when value unchanged
  - `MockDisplay` clamps brightness 0–7
- [x] **2.6** Hardware factory (`hardware/factory.py`)
  - File: `hardware/factory.py` — `create_hardware_factory(config)`
  - Detects Pi via `/sys/firmware/devicetree/base/model` device-tree check
  - `dev_mode=True` or non-Pi → `MockHardwareFactory`
  - Pi → `GPIOHardwareFactory` (Phase 4, falls back to mock if not available)
  - `mock_factory.py` — `MockHardwareFactory` with `set_screen()` injection
- [x] **2.7** Integration: `python -m boss.main` launches NiceGUI on `:8080` with dev panel on Windows
- [ ] **2.8** Integration tests using `nicegui.testing` (deferred — manual smoke test sufficient for now)
- [x] **2.9** Unit tests for mock hardware (33 tests)
  - `test_in_memory_screen.py` — 7 tests: all display methods, clear, call_log
  - `test_mock_hardware.py` — 20 tests: all mock classes with simulate helpers
  - `test_mock_factory.py` — 6 tests: interface conformance, set_screen, attribute access

**Acceptance:** `python -m boss.main` launches NiceGUI on `:8080`, browser shows main screen + dev panel, clicking virtual Go button triggers app launch flow, LED indicators update in real-time.

---

## Phase 3 — Mini-App Framework & Migration

- [x] **3.1** Enhance core API — `AppAPI.get_secret()`, `_ScopedEventBus.publish_threadsafe()`, `AppAPI.get_all_app_summaries()`
  - `AppLauncher` now accepts `secrets`, builds `app_summaries` from switch map
  - `SystemManager` passes secrets to launcher
- [x] **3.2** Enhance `migrate_manifest_v2()` — strip `external_apis`, map `timeout_behavior` `"none"`/`"rerun"` → `"return"` with 900s timeout
- [x] **3.3** Create shared `_lib` library (`apps/_lib/`)
  - `error_utils.py` — `summarize_error()` for requests exceptions (timeout, DNS, SSL, etc.)
  - `paginator.py` — `TextPaginator` with LED callbacks, `wrap_plain()`, `wrap_with_prefix()`, `wrap_events()`, `wrap_paragraphs()`
  - `http_helpers.py` — `fetch_json()` with retry/backoff, `fetch_text()`
- [x] **3.4** Migrate system/utility apps: `hello_world`, `list_all_apps`, `admin_startup`
- [x] **3.5** Migrate `admin_shutdown` — menu-driven shutdown/reboot/exit via `publish_threadsafe`
- [x] **3.6** Migrate 13 simple network apps: `dad_joke_generator`, `quote_of_the_day`, `random_useless_fact`, `color_of_the_day`, `name_that_animal`, `tiny_poem`, `today_in_music`, `word_of_the_day`, `flights_leaving_heathrow`, `flight_status_favorite_airline`, `moon_phase`, `space_update`, `local_tide_times`
- [x] **3.7** Migrate 3 pagination apps: `breaking_news`, `bird_sightings_near_me`, `on_this_day` — Yellow=prev / Green=refresh / Blue=next
- [x] **3.8** Migrate 4 static/asset apps: `app_jokes`, `random_emoji_combo`, `random_local_place_name`, `public_domain_book_snippet`
  - Assets copied from v2: `jokes.json`, `emoji.json`, `places.json`, `sample.txt`
- [x] **3.9** Migrate 5 special-case apps: `current_weather` (Open-Meteo, no key), `top_trending_search` (rewritten for SerpApi), `internet_speed_check` (placeholder), `constellation_of_the_night` (static), `joke_of_the_moment` (JokeAPI two-part reveal)
- [x] **3.10** Update `app_mappings.json` — 29 apps mapped, removed `admin_wifi_configuration` (252) and `admin_boss_admin` (254) → deferred to Phase 5
- [x] **3.11** Unit tests (228 new tests, 321 total)
  - `test_error_utils.py` — 11 tests for `summarize_error`
  - `test_paginator.py` — 15 tests for paginator and wrap helpers
  - `test_http_helpers.py` — 6 tests for `fetch_json`/`fetch_text` with mocked requests
  - `test_manifest_scan.py` — parametrized over all 29 apps (exists, valid JSON, parses, entry_point, defines `run()`)
  - `test_app_smoke.py` — import tests for all 29 apps + run smoke tests for 10 local-only apps
  - `test_app_api_phase3.py` — tests for `get_secret`, `get_all_app_summaries`, `publish_threadsafe`
  - `test_manifest_migration.py` — tests for enhanced `migrate_manifest_v2`

**Acceptance:** 29 apps migrated, each has `run(stop_event, api)` + `manifest.json`, all 321 tests pass, no direct hardware imports in any app. 2 admin apps deferred to Phase 5.

---

## Phase 4 — GPIO Hardware Backend

- [x] **4.1** Add `cleanup()` to `HardwareFactory` ABC (concrete no-op) + wire from `SystemManager.shutdown()`
- [x] **4.2** `gpio/gpio_hardware.py` — 6 GPIO component classes
  - `GPIOButtons` — `gpiozero.Button` per colour, `bounce_time=0.05`, zero-arg callbacks
  - `GPIOGoButton` — `gpiozero.Button`, `bounce_time=0.2`
  - `GPIOLeds` — `gpiozero.LED` per colour, boolean on/off, internal state tracking
  - `GPIOSwitches` — 74HC151 MUX via `DigitalInputDevice` + 3 `DigitalOutputDevice` select lines, daemon polling thread at ~20 Hz, auto-starts in `__init__`
  - `GPIODisplay` — `python-tm1637` TM1637, `show_number()`, `clear()`, `set_brightness(0–7)`
  - `GPIOSpeaker` — placeholder (logs calls, no real audio)
  - All classes have `cleanup()` methods; gpiozero/tm1637 imports guarded for Windows patchability
- [x] **4.3** `gpio/gpio_factory.py` — `GPIOHardwareFactory`
  - Sets `LGPIOFactory` pin factory in `__init__` (not at module import)
  - Eagerly creates all 6 components; `set_screen()` injection for NiceGUI
  - `cleanup()` delegates to all components, `create_screen()` raises if not injected
- [x] **4.4** Update `main.py` — unified screen injection (both mock and GPIO factories)
- [x] **4.5** Populate `boss_config.json` with real V2 pin numbers
  - Switches: data=8, S0=23, S1=24, S2=25
  - Buttons: red=26, yellow=19, green=13, blue=6; Go=17
  - LEDs: red=21, yellow=20, green=16, blue=12
  - TM1637: CLK=5, DIO=4
  - Location: 51.8167, -0.8146 (user's actual location)
- [x] **4.6** Unit tests (43 new, 364 total) — all GPIO classes tested via mocked gpiozero/tm1637
  - `test_gpio_buttons.py` — 6 tests: pins, pull_up, bounce_time, callbacks, cleanup, interface
  - `test_gpio_go_button.py` — 4 tests: pin, callback, cleanup, interface
  - `test_gpio_leds.py` — 7 tests: pins, on/off, state tracking, all_off, cleanup, interface
  - `test_gpio_switches.py` — 8 tests: pins, initial value, all-on/off, change callback, pin sequencing, cleanup, interface
  - `test_gpio_display.py` — 8 tests: pins, show_number, fallback, clear, brightness, clamping, cleanup, interface
  - `test_gpio_factory.py` — 10 tests: interface compliance, all create_* methods, set_screen, raises without screen, cleanup idempotent
- [ ] **4.7** Test on actual Raspberry Pi hardware
- [ ] **4.8** Verify LED/button parity (LED gating) works end-to-end on Pi

**Acceptance:** All GPIO classes implement V3 ABCs, 364 tests pass on Windows via mocked gpiozero. Pi hardware testing (4.7–4.8) requires deployment.

---

## Phase 5 — Pi Deployment & Polish

- [x] **5.1** Standardise deploy artifacts to `rpi` username
  - Fixed `deploy/deploy.sh` (`PI_USER="rpi"`), updated `deploy/PI_SETUP.md` (~8 references), updated `.github/instructions/deployment.md`
- [x] **5.2** Harden `deploy/boss.service` — systemd security directives
  - `NoNewPrivileges=true`, `PrivateTmp=true`, `ProtectSystem=strict`, `ReadWritePaths=/opt/boss/logs /opt/boss/secrets`
  - `MemoryMax=512M`, `CPUQuota=80%`, `SupplementaryGroups=gpio`, `EnvironmentFile=/opt/boss/secrets/secrets.env`
  - Updated inline templates in `PI_SETUP.md` and `.github/instructions/deployment.md`
- [x] **5.3** Update `secrets/secrets.sample.env` — all 10 `BOSS_APP_*` keys with comments showing which app uses each
- [x] **5.4** Create `scripts/validate_manifests.py`
  - Loads Pydantic `AppManifest` for each `apps/*/manifest.json`
  - Validates entry_point file exists and defines `run()`
  - Cross-references `app_mappings.json` switch mappings
  - Reports `required_env` keys vs `secrets.sample.env`
  - ASCII-safe output (no Unicode symbols — works on Windows cp1252)
- [x] **5.5** Implement real `reboot()` / `shutdown()` in `SystemManager`
  - `subprocess.Popen(["sudo", "reboot"])` / `["sudo", "shutdown", "-h", "now"]`
  - Guarded by `dev_mode` (logs warning instead on Windows)
  - Public properties: `app_manager`, `app_runner` (needed by admin page)
- [x] **5.6** Create `ui/admin_page.py` — NiceGUI `/admin` route
  - `AdminPage` class with `setup_page()` registering `/admin` and `/admin/wifi`
  - Status card: hostname, Python version, uptime, dev_mode, current app, port
  - App list table with switch mappings, descriptions, required_env status
  - Log viewer: last 200 lines of `boss.log`, auto-refresh toggle
  - Secrets status overview (which keys set, which apps need them)
  - Git update button (hidden in dev_mode)
  - WiFi management subpage: current connection, network scan, SSID+password connect form
- [x] **5.7** Create `admin_boss_admin` mini-app (switch 254)
  - Shows `/admin` URL on kiosk screen with auto-detected IP
  - Mapped in `app_mappings.json`
- [x] **5.8** Create `admin_wifi_configuration` mini-app (switch 252)
  - Uses `nmcli` for WiFi scan/connect on Pi, informational fallback in dev mode
  - Directs to `/admin/wifi` for password entry
  - Mapped in `app_mappings.json`
- [x] **5.9** Wire admin page in `main.py` — deferred setup via `on_startup` (after `system.start()`)
- [x] **5.10** Unit tests (41 new, 405 total)
  - `test_validate_manifests.py` — 4 tests: script exists, runs successfully, finds 31 apps, reports switch mappings
  - `test_admin_page.py` — 3 tests: init, setup_page method, stores dependencies
  - `test_admin_boss_admin.py` — 5 tests: displays URL, configured port, IP detection, fallback, stop_event
  - `test_admin_wifi.py` — 8 tests: dev mode, no nmcli, URL, IP, nmcli detection, stop_event
  - `test_system_manager_phase5.py` — 7 tests: properties, dev_mode guards, subprocess calls, sys.exit
  - `test_manifest_scan.py` and `test_app_smoke.py` automatically pick up 2 new admin apps (31 total)
- [x] **5.11** Final cleanup: removed unused import, updated `README.md` (admin panel + scripts in features/structure)
- [ ] **5.12** Pi OS preparation: Desktop image, autologin, X11, no screen blanking (documented in PI_SETUP.md)
- [ ] **5.13** End-to-end testing on Pi: switches → Go → app renders in kiosk Chromium

**Acceptance:** `deploy.sh` pushes code to Pi, `sudo systemctl restart boss boss-kiosk` brings up the full system, Chromium kiosk shows BOSS UI, all physical inputs work, all apps render correctly. Admin panel accessible at `/admin`.

---

## Progress Summary

| Phase | Status | Tasks | Tests |
|-------|--------|-------|-------|
| 0 — Foundation | **Complete** | 8/8 done | — |
| 1 — Core Rewrite | **Complete** | 15/15 done | 60 |
| 2 — NiceGUI UI | **Complete** | 8/9 done (integration test deferred) | 33 |
| 3 — Mini-App Migration | **Complete** | 11/11 done | 228 |
| 4 — GPIO Backend | **Complete** | 6/8 done (Pi hardware testing deferred to deployment) | 43 |
| 5 — Deployment | **Complete** | 11/13 done (Pi testing deferred to deployment) | 41 |
| **Total** | | | **405** |
