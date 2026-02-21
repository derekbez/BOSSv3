# Architecture & Principles

## Overview

B.O.S.S. v3 is a NiceGUI application with an event-driven architecture. All hardware
interaction flows through an abstraction layer; all screen output renders in a browser
via NiceGUI.

## Package Layout (src-layout)

```
src/boss/
  main.py              # Composition root — wires everything, calls ui.run()
  core/                # Business logic: event bus, app management, orchestration
    models/            # Pydantic models (config, manifest, hardware state)
    interfaces/        # ABCs for hardware components
  hardware/            # Platform backends: gpio/ (Pi), mock/ (testing)
  ui/                  # NiceGUI: layout, screen API, dev simulation panel
  apps/                # Mini-app directories (self-contained)
  config/              # JSON config files, config_manager, secrets_manager
  logging/             # setup_logging(), ContextualLogger
```

## Key Principles

1. **Composition root** — `main.py` wires all dependencies. No hidden side-effects at import.
2. **Dependency injection** — all services receive dependencies via constructor.
3. **Event-driven** — hardware callbacks → event bus → handlers. No polling in app code.
4. **Single UI path** — NiceGUI serves browser on both Pi (kiosk Chromium) and dev (any browser).
5. **Hardware abstraction** — ABCs in `core/interfaces/`; GPIO and Mock in `hardware/`.
6. **Mini-app isolation** — apps only use `api.*`; never import hardware or core directly.
7. **Pydantic everywhere** — config, manifests, events all validated via Pydantic models.

## Anti-Patterns (Do NOT)

- Import from `boss.hardware.gpio` in app code (use `api.*`)
- Use `time.sleep()` in apps (use `stop_event.wait(interval)`)
- Poll hardware state (subscribe to events)
- Create global/module-level state (pass via DI)
- Add `wrap`/`wrap_width` to hardware screen interface (UI layer handles layout)
- Access `boss.ui` from core (core is UI-agnostic)

## Dependency Flow

```
main.py → core (event_bus, managers) → hardware (GPIO/mock)
main.py → ui (layout, screen, dev_panel) → core (event_bus)
apps → api (scoped) → core → hardware
```

UI depends on core. Core does NOT depend on UI. Hardware does NOT depend on core.
