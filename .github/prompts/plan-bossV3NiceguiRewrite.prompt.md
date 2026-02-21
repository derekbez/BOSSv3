## Plan: B.O.S.S. v3 — NiceGUI Rewrite

### TL;DR
Rewrite B.O.S.S. as a **NiceGUI application** running on Pi OS Desktop in kiosk mode. Keep the proven concepts (event bus, hardware abstraction, mini-app plugin system, manifest-driven configuration) but fix the accumulated issues: dead code, interface drift, no real screen rendering, broken config propagation, threading tangles. The browser becomes the *only* screen backend (replacing Rich/Textual/framebuffer), giving you full HTML/CSS rendering for text, images, tables, and animations — on both Pi (kiosk Chromium) and Windows (dev browser). The result is a single unified UI path, dramatically simpler screen API, and a robust mini-app authoring experience.

**Key decisions:**
- Python stays. NiceGUI chosen for UI.
- Pi OS Desktop (Bookworm 64-bit) with Chromium kiosk replaces Lite + terminal.
- Clean rewrite preserving architectural concepts, not incremental refactoring.
- Simple deployment (SSH + rsync), no Docker/CI.

---

### Steps

**Phase 0 — Foundation & Project Setup**

1. Create a new project root (e.g., `BOSSv3/`) alongside `BOSSv2/` so you can reference the old code. Initialize venv, `pyproject.toml` (modern packaging, replaces `requirements/` txt files), and a `src/boss/` layout using the [src-layout convention](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/).

2. Define dependencies in `pyproject.toml`: `nicegui>=2.0`, `gpiozero` (Pi only), `lgpio` (Pi only), `python-tm1637` (Pi only), `requests>=2.32`, `pydantic>=2.0` (replace raw dataclasses for config/manifest validation — NiceGUI already bundles it).

3. Set up the directory structure:
   ```
   src/boss/
     __init__.py
     main.py              # Composition root + ui.run()
     core/
       event_bus.py        # Rewritten, async-native
       app_manager.py      # App discovery & manifest loading
       app_runner.py       # Mini-app lifecycle
       system_manager.py   # Decomposed (see step 8)
       models/             # Pydantic models for Config, Manifest, HardwareState
       interfaces/         # ABCs for hardware
     hardware/
       factory.py          # Detect platform, create backend
       gpio/               # Real Pi hardware (buttons, LEDs, switches, display, speaker)
       mock/               # Testing backend
     ui/
       layout.py           # NiceGUI page layout (header, screen area, status bar)
       screen.py           # Screen API implementation (renders into NiceGUI container)
       dev_panel.py        # Dev-mode hardware simulation panel (replaces WebUI)
     apps/                 # Mini-app directories (migrated from v2)
     config/
       boss_config.json
       app_mappings.json
       config_manager.py
       secrets_manager.py
   ```

**Phase 1 — Core Rewrite**

4. **Event bus** — rewrite `boss/core/event_bus.py` as an async-aware event bus. Use `asyncio.Queue` instead of `threading.Queue`. Provide a `publish_threadsafe(event_type, payload)` method that GPIO callback threads can safely call (internally uses `asyncio.run_coroutine_threadsafe`). Drop the typed `DomainEvent` subclasses in `boss/core/events/domain_events.py` — they're dead code; keep the simple `(event_type: str, payload: dict)` pattern but add a Pydantic `Event` model for structure.

5. **Config & manifest models** — replace the hand-rolled dataclasses in `boss/core/models/` with Pydantic `BaseModel` classes. This **fixes the critical config bug** where `boss/core/models/app.py` silently drops the `config` field from manifests because `known_fields` doesn't include it. With Pydantic, extra fields are either allowed (`model_config = ConfigDict(extra="allow")`) or explicitly defined. Define `AppManifest` with an explicit `config: dict[str, Any] = {}` field.

6. **Hardware interfaces** — keep the ABC approach from `boss/core/interfaces/hardware.py` but fix the interface drift. Remove `wrap`/`wrap_width` from hardware screen implementations — **wrapping is the UI layer's responsibility, not the hardware's**. Simplify `ScreenInterface` to just `display_text(text, style)`, `display_html(html)`, `display_image(path)`, `clear()`. The NiceGUI screen implementation will handle all layout/formatting.

7. **Hardware factory** — simplify `boss/hardware/factory.py`. Two backends: `gpio` (real Pi) and `mock` (testing). Remove the `webui` backend entirely — there's no "WebUI hardware" anymore because the browser IS the production UI. On Windows (no GPIO), the system creates mock hardware + a dev simulation panel in NiceGUI.

8. **Decompose SystemManager** — the current `boss/core/system_manager.py` is 618 lines handling too many concerns. Split into:
   - `SystemManager` — startup/shutdown orchestration only (~100 lines)
   - `AppLauncher` — Go-button handling, app transition logic, timeout management (extracted from `SystemManager`)
   - `HardwareEventBridge` — wires hardware callbacks → event bus (extracted from `SystemManager` + `boss/core/event_handlers.py`)

**Phase 2 — NiceGUI UI Layer**

9. **Main page layout** (`ui/layout.py`) — define a single NiceGUI `@ui.page('/')` with:
   - A full-screen container for the mini-app's screen output (the "main screen")
   - A small status bar (current switch value, active app name, system status)
   - Use `@ui.refreshable` for the screen container so mini-apps can push arbitrary content

10. **Screen API** (`ui/screen.py`) — implement the new `ScreenInterface` backed by NiceGUI elements. When `api.screen.display_text("Hello")` is called from a mini-app thread, it marshals to the NiceGUI event loop via `asyncio.run_coroutine_threadsafe`, clears the screen container, and creates a `ui.label` / `ui.html` / `ui.markdown` element. For `display_image(path)`, create a `ui.image(path)`. This gives you **real image rendering** (which no v2 backend ever achieved). For rich content, allow `display_html(html_string)` so apps can render tables, styled text, etc.

11. **Dev simulation panel** (`ui/dev_panel.py`) — on non-Pi platforms, render an additional NiceGUI panel (collapsible sidebar or overlay) with virtual buttons, switch slider (0–255), LED indicators, and a 7-segment display readout. This replaces the entire WebUI backend + FastAPI + WebSocket + static HTML/JS/CSS stack from v2 with ~150 lines of Python using NiceGUI's built-in components. Wire the virtual buttons to the event bus like the real GPIO buttons.

12. **Main entry** (`main.py`) — composition root pattern preserved:
    - Load config → create event bus → detect platform → create hardware factory → create hardware → create app manager → create system manager
    - Use `app.on_startup` to initialize hardware monitoring, start event bus, run the startup app
    - Call `ui.run(host='0.0.0.0', port=8080, reload=False, show=False)` — this blocks and serves the UI
    - On Pi, a systemd service launches this; Chromium kiosk opens `http://localhost:8080`

**Phase 3 — Mini-App Migration**

13. **New mini-app contract** — `run(stop_event, api)` stays. The `api` object is essentially the same as `boss/core/api.py` but with the simpler screen API. Mini-apps don't need to change much — `api.screen.display_text()` still works, it just renders in a browser now. Add new capabilities: `api.screen.display_html()`, `api.screen.display_image()` (now actually works!), `api.screen.display_markdown()`.

14. **Migrate mini-apps** — copy each app from `boss/apps/` into the new project. Most will work with minimal changes since they use `api.*` exclusively. Prioritize the representative set: `hello_world`, `list_all_apps`, `current_weather`, `app_jokes`, admin apps. Then migrate the rest.

15. **Fix inherited issues during migration:**
    - `list_all_apps` — use manifest `config.entries_per_page` instead of hardcoded `per_page = 24`
    - `admin_startup` — remove non-standard `**kwargs` from signature
    - All apps' `finally` blocks — standardize cleanup pattern
    - Port `boss/apps/_error_utils.py` for the HTTP error summarization

**Phase 4 — Pi Deployment Setup**

16. **Pi OS preparation** — flash Pi OS Desktop (64-bit Bookworm), enable autologin via `raspi-config`, disable screen blanking, switch to X11 backend (for `unclutter` support to hide mouse cursor).

17. **Kiosk systemd service** — two units:
    - `boss.service` — runs `python -m boss.main`, `After=network-online.target graphical.target`
    - `boss-kiosk.service` — launches `chromium-browser --kiosk --noerrdialogs --incognito http://localhost:8080`, `After=boss.service`. Waits for the NiceGUI server to be ready before opening.

18. **Deploy script** — simple `rsync`-based script (keep the approach from `scripts/boss_remote_manager.py`):
    ```
    rsync -avz --exclude '.venv' --exclude '__pycache__' src/ pi@boss:/opt/boss/
    ssh pi@boss 'sudo systemctl restart boss'
    ```

**Phase 5 — Testing & Polish**

19. **Testing strategy** — preserve the good patterns from `tests/conftest.py` and `tests/helpers/`. Use `MockHardwareFactory` for unit tests (no NiceGUI needed). For integration tests, NiceGUI has built-in test support via `nicegui.testing` — use `Screen` fixture for UI assertions. Fix legacy test directory naming (`application/` → `core/`, `infrastructure/` → `hardware/`).

20. **Manifest validation** — port `scripts/validate_manifests.py` using the new Pydantic `AppManifest` model, which gives you validation for free. Run as a pre-commit check.

21. **Final cleanup** — remove dead code patterns that exist in v2:
    - No typed domain event classes (unused)
    - No `RichFramebufferWrapper` (unimplemented TODO)
    - No `PerformanceMonitor` / `performance_timer` (dead code)
    - No `GPIOGoButton._go_button_callback()` (legacy RPi.GPIO)
    - No separate WebUI hardware backend
    - No duplicate WebSocket connections

---

### Verification

- **Unit tests**: `pytest tests/unit/` — all core logic (event bus, app manager, app runner, config) tested with mock hardware, no UI dependency
- **Integration tests**: `pytest tests/integration/` — full system lifecycle using `nicegui.testing.Screen` for UI assertions
- **Smoke tests**: For each mini-app, verify it starts, renders something to screen, and shuts down cleanly
- **Manual on Pi**: Set switches to various values, press Go, verify apps display correctly in kiosk Chromium, verify LED/button parity
- **Manual on Windows**: Run `python -m boss.main`, open browser, verify dev panel simulates hardware correctly
- **Manifest validation**: `python -m boss.scripts.validate_manifests` passes for all apps

---

### Decisions

- **NiceGUI over extending current WebUI**: Eliminates the dual-path problem (terminal screen + browser screen), removes ~800 lines of WebUI plumbing (FastAPI endpoints, WebSocket manager, static JS/CSS), and gives mini-apps real rendering capabilities (images, HTML, markdown)
- **Pi OS Desktop over Lite**: Required for Chromium kiosk; the ~500MB extra disk space is negligible on modern SD cards; gain vastly better rendering
- **Pydantic over dataclasses**: Fixes the config-drop bug structurally, provides validation and serialization for free, already a NiceGUI dependency
- **Two hardware backends (gpio + mock) instead of three**: The "webui" backend was a hardware *simulation* — that role is now handled by the dev panel UI component, which is cleaner because it's just a UI concern, not a fake hardware layer
- **Async event bus**: NiceGUI runs on asyncio; making the event bus async-native avoids the thread-marshalling complexity that plagues v2's `WebUIScreen` ↔ `WebSocketManager` communication
- **`src/` layout**: Standard Python packaging practice, prevents accidental imports from the project root, cleaner `pip install -e .` support
- **Rewrite over refactor**: The number of intertwined issues (dead code, wrong screen backend naming, framebuffer TODOs, duplicate WebSocket connections, interface drift, broken config, 618-line SystemManager) means refactoring would touch nearly every file anyway — a focused rewrite with the same concepts is faster and produces a cleaner result
