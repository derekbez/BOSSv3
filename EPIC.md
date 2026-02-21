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
- [ ] **0.6** Create venv, install deps (`pip install -e ".[dev]"`)
- [ ] **0.7** Verify `python -c "import boss"` works
- [x] **0.8** Set up Copilot instructions (`.github/instructions/`, `.github/copilot-instructions.md`)

**Acceptance:** `pip install -e ".[dev]"` succeeds, `import boss` works, `pytest` runs (0 tests collected is fine).

---

## Phase 1 — Core Rewrite

- [ ] **1.1** Pydantic models: `BossConfig`, `HardwareConfig`, `SystemConfig`
  - Loads from `boss_config.json`, env overrides, validation
- [ ] **1.2** Pydantic models: `AppManifest` with explicit `config: dict[str, Any] = {}`
  - Fixes v2 config-drop bug; legacy manifest migration
- [ ] **1.3** Pydantic models: `HardwareState`, `LedColor`, `ButtonColor`, `AppStatus`
- [ ] **1.4** Hardware ABCs: `ButtonInterface`, `GoButtonInterface`, `LedInterface`, `SwitchInterface`, `DisplayInterface`, `ScreenInterface`, `SpeakerInterface`, `HardwareFactory`
  - Clean ScreenInterface: `display_text()`, `display_html()`, `display_image()`, `clear()`
  - No `wrap`/`wrap_width` on interface — that's the UI layer's job
- [ ] **1.5** Config manager: load JSON → apply env overrides → validate → return `BossConfig`
- [ ] **1.6** Secrets manager: thread-safe lazy loader, env > file > default
- [ ] **1.7** Async event bus
  - `asyncio.Queue`-based, handler dispatch on event loop
  - `publish_threadsafe()` for GPIO callback threads
  - `subscribe(event_type, handler, filter_dict=None)`
  - Auto-unsubscribe on handler error
  - Unit tests for subscribe/publish/filter/threadsafe/error-removal
- [ ] **1.8** App manager: scan `apps/` dirs, load manifests, bind to `app_mappings.json`, validate `required_env`
- [ ] **1.9** App runner: daemon thread per app, cooperative cancellation, timeout monitor, lifecycle events
- [ ] **1.10** AppLauncher: Go-button → snapshot switch → transition feedback → launch app → post-app cleanup
- [ ] **1.11** HardwareEventBridge: wire hardware callbacks → event bus (LED gating for buttons)
- [ ] **1.12** SystemManager: startup + shutdown orchestration only (~100 lines)
- [ ] **1.13** AppAPI: scoped event bus, screen API, hardware API, config access, logging
  - `get_app_config()` returns manifest `config`; `get_config_value()` with defaults
  - `get_global_location()` resolution
  - `get_app_path()`, `get_asset_path()`
- [ ] **1.14** Logging: `setup_logging()`, `ContextualLogger`, rotating file handler
- [ ] **1.15** Unit tests for all Phase 1 modules

**Acceptance:** All core modules importable, unit tests green, event bus handles async + threadsafe publish, config round-trips correctly, manifest `config` field preserved.

---

## Phase 2 — NiceGUI UI Layer

- [ ] **2.1** `ui/screen.py` — `NiceGUIScreen` implementing `ScreenInterface`
  - `display_text()` → marshals to event loop → renders `ui.label`/`ui.html`
  - `display_html()` → renders arbitrary HTML
  - `display_image()` → renders `ui.image` (real image rendering!)
  - `display_markdown()` → renders `ui.markdown`
  - `clear()` → clears container
  - Thread-safe: all calls from mini-app threads marshal via `run_coroutine_threadsafe`
- [ ] **2.2** `ui/layout.py` — main page with `@ui.page('/')`
  - Full-screen app container
  - Status bar (switch value, active app, system state)
  - Dark theme
- [ ] **2.3** `ui/dev_panel.py` — dev-mode hardware simulation
  - Virtual buttons (red, yellow, green, blue, Go)
  - Switch slider (0–255) with binary display
  - LED indicators with color glow
  - 7-segment display readout
  - Only rendered when `is_pi = False`
- [ ] **2.4** `main.py` — composition root
  - Config → EventBus → HardwareFactory → Hardware → AppManager → SystemManager
  - `app.on_startup` hook for initialization
  - `ui.run()` blocks main thread
- [ ] **2.5** Mock hardware backend (`hardware/mock/`)
  - All interfaces implemented with in-memory state
  - `simulate_press()`, `simulate_switch_change()` for testing
- [ ] **2.6** Hardware factory (`hardware/factory.py`)
  - Detects gpio vs mock (no webui backend)
  - On Windows/non-Pi → mock + dev panel
- [ ] **2.7** Integration: run `python -m boss.main` on Windows, see NiceGUI page in browser with dev panel
- [ ] **2.8** Integration tests using `nicegui.testing`

**Acceptance:** `python -m boss.main` launches NiceGUI on `:8080`, browser shows main screen + dev panel, clicking virtual Go button triggers app launch flow, LED indicators update in real-time.

---

## Phase 3 — Mini-App Migration

- [ ] **3.1** Port `_error_utils.py` (HTTP error summarization)
- [ ] **3.2** Migrate `hello_world` — baseline test that buttons, LEDs, screen work
- [ ] **3.3** Migrate `list_all_apps` — fix hardcoded `per_page`, use manifest config
- [ ] **3.4** Migrate `admin_startup` — remove `**kwargs`, clean signature
- [ ] **3.5** Migrate `admin_shutdown` — menu-driven shutdown/reboot/exit
- [ ] **3.6** Migrate `app_jokes` — static asset loading
- [ ] **3.7** Migrate `current_weather` — network + periodic refresh
- [ ] **3.8** Migrate remaining network apps: `dad_joke_generator`, `word_of_the_day`, `quote_of_the_day`, `random_useless_fact`, `on_this_day`, `breaking_news`, `space_update`, `top_trending_search`
- [ ] **3.9** Migrate remaining static apps: `tiny_poem`, `random_emoji_combo`, `random_local_place_name`, `public_domain_book_snippet`, `today_in_music`, `color_of_the_day`
- [ ] **3.10** Migrate specialty apps: `moon_phase`, `local_tide_times`, `constellation_of_the_night`, `internet_speed_check`
- [ ] **3.11** Migrate flight apps: `flights_leaving_heathrow`, `flight_status_favorite_airline`
- [ ] **3.12** Migrate `admin_wifi_configuration`, `admin_boss_admin`
- [ ] **3.13** Migrate `bird_sightings_near_me`, `name_that_animal`, `joke_of_the_moment`
- [ ] **3.14** Copy `app_mappings.json` and `boss_config.json` (adapted for v3)
- [ ] **3.15** Smoke tests for all migrated apps
- [ ] **3.16** Standardize all apps' `finally` cleanup blocks

**Acceptance:** All ~30 apps migrated, each has `run(stop_event, api)` + `manifest.json`, smoke tests pass, no direct hardware imports in any app.

---

## Phase 4 — GPIO Hardware Backend

- [ ] **4.1** `gpio/gpio_hardware.py` — `GPIOButtons`, `GPIOGoButton`, `GPIOLeds`, `GPIOSwitches`, `GPIODisplay`, `GPIOSpeaker`
  - Uses `gpiozero` + `lgpio` pin factory
  - No dead legacy callbacks
- [ ] **4.2** `gpio/gpio_factory.py` — `GPIOHardwareFactory`
  - No screen backend in hardware layer (NiceGUI handles all screen rendering)
- [ ] **4.3** Test on actual Raspberry Pi hardware
- [ ] **4.4** Verify LED/button parity (LED gating) works end-to-end on Pi

**Acceptance:** All physical hardware (8 switches via MUX, 4 color buttons, Go button, 4 LEDs, TM1637 display) works, events flow to NiceGUI screen.

---

## Phase 5 — Pi Deployment & Polish

- [ ] **5.1** Pi OS preparation: Desktop image, autologin, X11, no screen blanking
- [ ] **5.2** `deploy/boss.service` — systemd unit for BOSS server
- [ ] **5.3** `deploy/boss-kiosk.service` — systemd unit for Chromium kiosk
- [ ] **5.4** `deploy/deploy.sh` — rsync-based deploy script
- [ ] **5.5** `secrets/secrets.sample.env` — template for API keys
- [ ] **5.6** Manifest validation script (`scripts/validate_manifests.py`) using Pydantic
- [ ] **5.7** End-to-end testing on Pi: switches → Go → app renders in kiosk Chromium
- [ ] **5.8** Final cleanup pass: remove any dead code, verify all docs accurate
- [ ] **5.9** Archive BOSSv2 (tag/branch) and promote BOSSv3

**Acceptance:** `deploy.sh` pushes code to Pi, `sudo systemctl restart boss boss-kiosk` brings up the full system, Chromium kiosk shows BOSS UI, all physical inputs work, all apps render correctly.

---

## Progress Summary

| Phase | Status | Tasks |
|-------|--------|-------|
| 0 — Foundation | **In Progress** | 6/8 done |
| 1 — Core Rewrite | Not Started | 0/15 |
| 2 — NiceGUI UI | Not Started | 0/8 |
| 3 — Mini-App Migration | Not Started | 0/16 |
| 4 — GPIO Backend | Not Started | 0/4 |
| 5 — Deployment | Not Started | 0/9 |
