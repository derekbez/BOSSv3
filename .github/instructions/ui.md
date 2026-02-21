# NiceGUI UI Layer

## Overview

NiceGUI is the sole screen backend for B.O.S.S. v3. It serves a web page that renders
all mini-app output. On Raspberry Pi, Chromium opens in kiosk mode pointing at
`http://localhost:8080`. On dev machines, any browser works.

## Key Files

- `ui/layout.py` — `@ui.page('/')` with main screen container + status bar
- `ui/screen.py` — `NiceGUIScreen` implementing `ScreenInterface`
- `ui/dev_panel.py` — hardware simulation controls (non-Pi only)

## Thread Safety

Mini-apps run in daemon threads. NiceGUI UI must only be updated from the asyncio
event loop. The `NiceGUIScreen` marshals all calls:

```python
class NiceGUIScreen:
    def display_text(self, text, **kwargs):
        asyncio.run_coroutine_threadsafe(
            self._render_text(text, **kwargs),
            self._loop
        )
```

## Dev Panel

On non-Pi platforms, `dev_panel.py` renders a sidebar with:

- **Virtual buttons** — Red, Yellow, Green, Blue, Go
- **Switch slider** — 0–255 with binary readout
- **LED indicators** — colored circles that glow when on
- **7-segment readout** — shows current display value

All controls publish/subscribe events through the same event bus as real hardware.
This replaces the entire v2 WebUI backend (FastAPI + WebSocket + HTML/JS/CSS) with
~150 lines of Python.

## Screen API for Apps

Apps call `api.screen.*` which delegates to `NiceGUIScreen`:

| Method | Renders |
|--------|---------|
| `display_text(text, font_size, color)` | `ui.label` styled with CSS |
| `display_html(html)` | `ui.html` — full HTML/CSS |
| `display_image(path)` | `ui.image` — real image rendering |
| `display_markdown(md)` | `ui.markdown` |
| `clear()` | Clears the screen container |

## Dark Theme

The UI uses a dark theme matching the hardware aesthetic. Set via:

```python
ui.dark_mode().enable()
```

## No Multiple Pages

Single-page app. Mini-app output swaps within a `@ui.refreshable` container.
The status bar is persistent. No page navigation.
