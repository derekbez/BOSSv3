# B.O.S.S. v3 — Board Of Switches and Screen

A modular Raspberry Pi mini-app platform with physical hardware controls (toggle switches, buttons, LEDs, 7-segment display) and a browser-based UI powered by [NiceGUI](https://nicegui.io/).

## Features

- **8 toggle switches** (via 74HC151 multiplexer) select apps by binary value (0–255)
- **Go button** launches the selected mini-app
- **Color-coded buttons & LEDs** (Red, Yellow, Green, Blue) for in-app interaction
- **TM1637 7-segment display** shows current switch value
- **Browser-based screen** (NiceGUI) renders text, images, HTML, and markdown
- **Kiosk mode** on Raspberry Pi (Chromium fullscreen on HDMI display)
- **Dev mode** on Windows/Mac with simulated hardware controls in the browser
- **50+ mini-apps**: weather, jokes, news, tide times, space updates, utilities, and games
- **Admin panel** at `/admin` — system status, editable global location, app config overrides, log viewer, secrets status + editing, WiFi management, and software update tools
- **Event-driven architecture** with async event bus
- **Plugin system** — each app is a self-contained directory with `main.py` + `manifest.json`

## Quick Start

### Prerequisites

- Python 3.11+
- (Optional) Raspberry Pi 4/5 with Pi OS Desktop for production mode

### Install & Run (Windows / Dev)

```bash
cd BOSSv3
python -m venv .venv
.venv\Scripts\Activate.ps1    # PowerShell
pip install -e ".[dev]"
python -m boss.main
```

Open `http://localhost:8080` in your browser.

For full Windows developer setup (run, stop, restart, troubleshooting), see
`deploy/WINDOWS_DEV_SETUP.md`.

### Install & Run (Raspberry Pi)

```bash
cd BOSSv3
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[pi,dev]"
python -m boss.main
```

Chromium kiosk opens automatically (see `deploy/` for systemd setup).

For Raspberry Pi provisioning and deployment details, see `deploy/PI_SETUP.md`.

## Project Structure

```
src/boss/
  main.py              # Entry point
  core/                # Event bus, app manager, system orchestration
    models/            # Pydantic models (config, manifest, state)
    interfaces/        # Hardware ABCs
  hardware/            # GPIO (Pi) and Mock (testing) backends
  ui/                  # NiceGUI layout, screen API, dev simulation panel
  apps/                # Mini-app directories
  config/              # JSON config, secrets manager
  logging/             # Logging setup
tests/                 # Unit and integration tests
deploy/                # systemd units, deploy script
scripts/               # validate_manifests.py and helpers
```

## Architecture

- **Event bus** — async pub/sub; hardware callbacks marshal via `publish_threadsafe()`
- **Hardware abstraction** — ABCs with GPIO and Mock implementations; LED/button parity enforced at manager level
- **Mini-app contract** — `def run(stop_event, api)` with scoped API for screen, hardware, events, config
- **NiceGUI** — single UI path for both Pi (kiosk Chromium) and dev (browser)
- **Pydantic** — all config and manifest validation; no silent field drops

## Mini-App Development

Create a directory in `src/boss/apps/your_app/` with:

- `main.py` — implements `def run(stop_event, api)`
- `manifest.json` — app metadata, timeout, tags, config

```python
def run(stop_event, api):
    api.screen.display_text("Hello from my app!")
    stop_event.wait()
```

Map it in `src/boss/config/app_mappings.json`:

```json
{ "42": "your_app" }
```

See `EPIC.md` for full project tracker and `.github/prompts/` for the rewrite plan.
