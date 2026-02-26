# BOSSv3 Improvement Plan

## Process Instructions

> **Research before coding.** For each item (or related group of items) below,
> thoroughly research the current implementation before writing any code.
> Read every affected file, trace the data flow, and confirm the root cause.
> Only then implement the fix.
>
> **Update documentation.** Every change must include corresponding updates to
> documentation — instruction files in `.github/instructions/`, code comments,
> docstrings, and the EPIC tracker as appropriate. No fix is complete until the
> docs reflect reality.
>
> **Pin diagram is golden truth.** `docs/RPi-GPIO-Pin-Diagram.md` is the
> authoritative reference for all GPIO pin assignments. If any config file,
> instruction doc, or code disagrees with that diagram, the diagram wins.
> Update the offending file to match.
>
> **Run tests after every change.** Confirm `pytest` passes before moving to
> the next item. If a change cannot be covered by an existing test, write one.

---

## Bugs (Fix First)

### 1. ~~Shutdown/reboot is silently broken~~ ✅ FIXED
**File:** `src/boss/apps/admin_shutdown/main.py` → `src/boss/core/system_manager.py`
**Problem:** `admin_shutdown` published `{"reason": "reboot"}` but `SystemManager._on_shutdown_requested` read `event.payload.get("action", "exit")`. Since `"action"` was never set, reboot and poweroff always fell through to the `"exit"` default.
**Fix applied:** Changed `admin_shutdown/main.py` to send both `action` and `reason` keys: `{"action": "reboot", "reason": "reboot"}`, `{"action": "shutdown", "reason": "poweroff"}`, `{"action": "exit", "reason": "exit_to_os"}`. System manager already reads these correctly.
**Tests:** `tests/unit/core/test_shutdown_payload.py` — 4 tests covering all three actions plus missing-action default.

### 2. ~~AppRunner timer leak~~ ✅ FIXED
**File:** `src/boss/core/app_runner.py`
**Problem:** A `threading.Timer` was started for each app but never cancelled if the app finished before timeout. Rapid Go-button presses could cause stale timers to set `stop_event` on already-finished apps.
**Fix applied:** Stored timer reference as `self._timer`. Added `_cancel_timer()` helper called in `stop()` and in the `_run_wrapper` `finally` block. Timer is set to `None` after cancellation.
**Tests:** `tests/unit/core/test_timer_cancellation.py` — 3 tests: timer cancelled after normal finish, cancelled on stop(), and no stale timer on rapid relaunch.

### 3. ~~Event subscriptions leak on browser refresh~~ ✅ FIXED
**Files:** `src/boss/ui/layout.py`, `src/boss/ui/dev_panel.py`
**Problem:** Event bus subscriptions were created every time the page rendered (F5 refresh). Old subscriptions were never cleaned up, creating duplicate handlers that accumulated.
**Fix applied:** Both files now track subscription IDs in a local `sub_ids` list and register a `ui.context.client.on_disconnect` callback that bulk-unsubscribes all IDs when the client disconnects.
**Tests:** `tests/unit/core/test_subscription_cleanup.py` — 4 tests verifying the track-and-unsubscribe pattern, double-unsubscribe safety, accumulation without cleanup, and correct behavior with cleanup.

---

## Architecture Improvements

### 4. ~~AppLauncher reaches into private `_switch_map`~~ ✅ FIXED
**File:** `src/boss/core/app_launcher.py`
**Problem:** Accesses `self._app_manager._switch_map` directly instead of using a public API.
**Fix applied:** Added `get_switch_map()` public method to `AppManager` returning a copy of the mapping. Updated `AppLauncher._build_app_summaries()` to use `self._app_manager.get_switch_map().items()` instead of the private attribute.

### 5. ~~factory.py mutates shared config~~ ✅ FIXED
**File:** `src/boss/hardware/factory.py`
**Problem:** Sets `config.system.dev_mode = True` as a side-effect, mutating the shared config object.
**Fix applied:** Removed config mutation from `factory.py`. Moved `dev_mode` assignment to `main.py` where it sets `config.system.dev_mode = True` based on `isinstance(factory, MockHardwareFactory)`. Updated test `test_hardware_factory.py` to assert the factory no longer mutates config.

### 6. ~~No graceful app handoff~~ ✅ FIXED
**File:** `src/boss/core/app_runner.py`
**Problem:** `run_app()` calls `stop()` then immediately starts a new app. The 5-second join timeout means the old app thread might still be running when the new one starts.
**Fix applied:** Added extended join timeout in `run_app()` — after calling `stop()`, waits up to 10s for the old thread to finish. Logs a warning if the thread is still alive after the extended wait, then proceeds.

### 7. ~~Single-client UI binding~~ ✅ FIXED
**File:** `src/boss/ui/screen.py`
**Problem:** `NiceGUIScreen.bind_container` binds to one client. If two browsers connect, only the last one gets updates.
**Fix applied:** Changed `NiceGUIScreen` from single `self._container` to `self._containers: set[ui.element]`. All render methods iterate over all containers with `RuntimeError` cleanup for stale clients. Added `unbind_container()` method. `layout.py` calls `unbind_container()` on client disconnect.

### 8. ~~Rename `boss.logging` package~~ ✅ FIXED
**File:** `src/boss/log_config/` (was `src/boss/logging/`)
**Problem:** Shadows stdlib `logging`, forcing every file to use `import logging as _logging`.
**Fix applied:** Renamed package to `boss.log_config`. Updated all 18 source files from `import logging as _logging` / `_logging.` to plain `import logging` / `logging.`. Updated `__init__.py`, `main.py`, `app_api.py` import paths. Updated `event_bus.md` and `EPIC.md` docs.

### 9. ~~Remove or integrate unused models~~ ✅ FIXED
**File:** `src/boss/core/models/state.py`
**Problem:** `AppStatus` and `HardwareState` enums are defined but never used.
**Fix applied:** Removed `AppStatus` enum (5 statuses, zero consumers) and `HardwareState` Pydantic model (duplicated what `HardwareEventBridge` tracks inline). Removed `pydantic` import from `state.py`. Cleaned up `__init__.py` re-exports. `LedColor` and `ButtonColor` remain (actively used).

---

## Security

### 10. No auth on `/admin` routes
**Files:** `src/boss/ui/admin_page.py`
**Problem:** Anyone on the local network can view system status, trigger `git pull`, read logs, and change WiFi.
**Fix:** Add basic authentication — even a simple shared-secret token or NiceGUI's built-in auth middleware.

### 11. WiFi passwords visible in process listing
**File:** `src/boss/ui/admin_page.py`
**Problem:** Passwords passed via `nmcli` command-line args are visible in `ps aux`.
**Fix:** Pipe credentials via stdin or use a connection file.

### 12. Log viewer exposes internal state
**File:** `src/boss/ui/admin_page.py`
**Problem:** The last 200 lines of `boss.log` are served unauthenticated.
**Fix:** Gate behind auth (same as #10).

---

## Testing Gaps

### 13. ~~No integration tests~~ ✅ FIXED
**Directory:** `tests/integration/`
**Problem:** Empty. No tests verify the full composition root or end-to-end event flow.
**Fix applied:** Created `tests/integration/test_go_button_flow.py` with 3 tests: (1) GO_BUTTON_PRESSED fires, app starts, renders on `InMemoryScreen`, and emits `APP_LAUNCH_REQUESTED` → `APP_STARTED` → `APP_FINISHED` lifecycle events; (2) unmapped switch shows error message on screen; (3) crashing app emits `APP_ERROR`. All tests use real `EventBus`, `AppManager`, `AppRunner`, `AppLauncher` wired to `MockHardwareFactory`.

### 14. ~~Smoke tests use hardcoded sleep~~ ✅ FIXED
**File:** `tests/unit/apps/test_app_smoke.py`
**Problem:** Uses `time.sleep(0.5)` instead of the `wait_for` helper from `tests/helpers/runtime.py`.
**Fix applied:** Added `wait_for_sync()` — a synchronous polling helper — to `tests/helpers/runtime.py`. Replaced the `time.sleep(0.5)` in `TestLocalAppSmoke.test_run` with `wait_for_sync(lambda: api.screen.texts or api.screen.htmls or api.screen.cleared > 0, timeout=3.0)`. Tests now complete as soon as the app renders, making them faster and more reliable.

### 15. ~~MockAPI drifts from AppAPI~~ ✅ FIXED
**File:** `tests/unit/apps/test_app_smoke.py`
**Problem:** `MockAPI` manually replicates every method of `AppAPI`. If `AppAPI` adds methods, tests won't catch the drift.
**Fix applied:** Replaced hand-rolled `MockAPI`, `MockHardwareAPI`, and `MockEventBus` with a `_make_mock_api()` factory that uses `unittest.mock.create_autospec(AppAPI, instance=True)`. This ensures the mock matches the real `AppAPI` surface — any missing or renamed method will raise `AttributeError`. `MockScreen` is retained for output inspection. Also added the previously missing `get_webui_port()` and `is_dev_mode()` stubs.

### 16. ~~Admin apps missing from smoke tests~~ ✅ FIXED
**Problem:** `admin_boss_admin` and `admin_wifi_configuration` have zero automated test coverage in the parametrized smoke suite.
**Fix applied:** Added both apps to the `LOCAL_APPS` set in `test_app_smoke.py`. They now run in the `TestLocalAppSmoke::test_run` parametrized suite alongside all other local apps. Also added `htmls` tracking to `MockScreen` since admin apps use `display_html()`, and updated the wait condition / assertion to check `texts`, `htmls`, and `cleared`.

### 17. ~~No test covers the shutdown payload bug~~ ✅ FIXED
**Problem:** The action/reason mismatch (#1) was a data-level bug a simple unit test would catch.
**Fix:** Covered by `tests/unit/core/test_shutdown_payload.py` (added as part of bug #1 fix).

---

## Developer Experience

### 18. ~~App type hints use `Any`~~ ✅ FIXED
**Problem:** Most apps declare `api: Any` instead of typing it as `AppAPI`, losing IDE autocompletion.
**Fix applied:** Updated all 29 app `main.py` files to use `TYPE_CHECKING` imports. Added `from typing import TYPE_CHECKING` and an `if TYPE_CHECKING: from boss.core.app_api import AppAPI` block. Changed `api: Any` → `api: "AppAPI"` and `from threading import Event` / `stop_event: Event` → `import threading` / `stop_event: threading.Event`. Apps `admin_boss_admin` and `admin_wifi_configuration` already had this pattern and were skipped.

### 19. ~~No hot-reload for apps~~ ✅ FIXED
**Problem:** Changing any app code requires restarting the entire NiceGUI server.
**Fix applied:** Two-pronged approach:
1. **Per-press module eviction** (`app_runner.py`): `_load_run_func()` now evicts all `boss.apps.*` entries from `sys.modules` before `importlib` loads the app module. This ensures every Go-button press picks up edits to app `main.py` and shared `_lib` helpers without restarting the server.
2. **`--dev` CLI flag** (`main.py`): Added `argparse` with `--dev` flag. When set, passes `reload=True` to `ui.run()` which enables Uvicorn auto-restart on any source file change (needed for edits to core modules outside `boss.apps`).

### 20. ~~Add `display_name` to manifests~~ ✅ FIXED
**Problem:** Manifest `name` must match directory name — no human-readable names possible.
**Fix applied:** Added optional `display_name: str | None = Field(default=None)` to `AppManifest` model with an `effective_display_name` property that returns `display_name` if set, otherwise title-cases the `name` field. Updated consumers: `app_runner.py` (APP_STARTED event), `app_launcher.py` (_transition_feedback and _build_app_summaries), and `main.py` (app resolver). Added human-readable `display_name` values to all 31 manifest.json files (e.g. "BOSS Admin", "Current Weather", "Flight Status: Favourite Airline").

---

## Incomplete / Stub Apps

### 21. `internet_speed_check` — fake data
**File:** `src/boss/apps/internet_speed_check/main.py`
**Fix:** Implement with `speedtest-cli` or `iperf3`, or mark clearly as placeholder in manifest.

### 22. `constellation_of_the_night` — static placeholder
**File:** `src/boss/apps/constellation_of_the_night/main.py`
**Fix:** Integrate a real data source (e.g., astronomyapi.com) or remove.

---

## Documentation vs Code Drift

### 23. Pin numbers don't match
**Golden truth:** `docs/RPi-GPIO-Pin-Diagram.md`
**Drifted file:** `.github/instructions/configuration.md` — shows placeholder pin numbers (`button_pins: {red:17, yellow:27, green:22, blue:23}`, `go_button_pin: 24`, `led_pins: {red:5, yellow:6, green:13, blue:19}`, `display_clk_pin: 20`, `display_dio_pin: 21`) that do not match the actual wiring.
**Code (correct):** `src/boss/config/boss_config.json` already matches the pin diagram.
**Fix:** Rewrite the JSON sample in `configuration.md` to exactly mirror `boss_config.json`, which reflects the real hardware wiring per the pin diagram.

### 24. Hardware docs say `PWMLED` — code uses `LED`
**Docs:** `.github/instructions/hardware.md`
**Code:** `src/boss/hardware/gpio/gpio_hardware.py`
**Fix:** Update docs to say `LED` (boolean on/off).

### 25. Docs say 10 Hz switch polling — code polls at ~20 Hz
**Docs:** `.github/instructions/hardware.md`
**Code:** `src/boss/hardware/gpio/gpio_hardware.py` uses 50ms sleep
**Fix:** Update docs to say ~20 Hz.

### 26. `output.screen.updated` event defined but never published
**File:** `src/boss/core/events.py`
**Fix:** Either publish it from `NiceGUIScreen` after updates, or remove the constant.

### 27. ~~Shutdown payload docs say `{action, reason}` — code only sends `{reason}`~~ ✅ FIXED
**Fix:** Resolved as part of bug #1. `admin_shutdown` now sends both `action` and `reason` keys, matching the event taxonomy documented in `event_bus.md`.

---

## Priority Matrix

| Priority | Items | Effort |
|----------|-------|--------|
| **P0 — Fix now** | ~~#1 (shutdown bug)~~, ~~#2 (timer leak)~~, ~~#3 (subscription leak)~~ | ~~Done~~ |
| **P1 — High value** | ~~#4 (encapsulation)~~, ~~#5 (config mutation)~~, ~~#6 (graceful handoff)~~, ~~#7 (multi-client)~~, ~~#8 (rename logging)~~, ~~#9 (unused models)~~, #10 (basic auth), ~~#13 (integration test)~~, ~~#15 (MockAPI drift)~~ | ~~#4-9, 13, 15 Done~~ |
| **P2 — Quality of life** | ~~#18 (type hints)~~, ~~#20 (display names)~~, ~~#14 (fix sleeps in tests)~~ | ~~Done~~ |
| **P3 — Nice to have** | ~~#19 (hot reload)~~, #21-22 (stub apps), #23-27 (docs sync) | ~~#19 Done~~ |
