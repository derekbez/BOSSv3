"""NiceGUIScreen — thread-safe screen rendering via NiceGUI.

Apps call ``display_text()``, ``display_html()``, etc. from daemon threads.
All calls are marshalled to the NiceGUI / asyncio event loop via
``asyncio.run_coroutine_threadsafe``.

The screen renders into a shared container element that is bound during
page setup by calling :meth:`bind_container`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from nicegui import ui

from boss.core.interfaces.hardware import ScreenInterface

_log = logging.getLogger(__name__)

# Default style for the screen canvas area
_SCREEN_STYLE = (
    "background: #000000; color: #ffffff; font-family: 'Courier New', monospace; "
    "width: 100%; aspect-ratio: 5/3; max-width: 800px; overflow: auto; "
    "display: flex; flex-direction: column; padding: 16px; box-sizing: border-box;"
)


class NiceGUIScreen(ScreenInterface):
    """Renders mini-app output into NiceGUI container(s).

    Thread-safety is achieved by marshalling every render call to the
    asyncio event loop via :func:`asyncio.run_coroutine_threadsafe`.

    Supports multiple connected clients — each calls :meth:`bind_container`
    and all bound containers are updated in parallel.

    Typical lifecycle::

        screen = NiceGUIScreen()
        # Later, inside @ui.page('/'):
        with ui.column() as container:
            ...
        screen.bind_container(container)
    """

    def __init__(self) -> None:
        self._containers: set[ui.element] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_container(self, container: ui.element) -> None:
        """Bind a NiceGUI container element and capture the event loop.

        Must be called from the NiceGUI event-loop context (e.g. inside
        ``@ui.page`` or ``app.on_startup``).  Multiple containers can
        be bound (one per connected client).
        """
        self._containers.add(container)
        self._loop = asyncio.get_event_loop()
        _log.debug("NiceGUIScreen bound container (total=%d)", len(self._containers))

    def unbind_container(self, container: ui.element) -> None:
        """Remove a container binding (call on client disconnect)."""
        self._containers.discard(container)
        _log.debug("NiceGUIScreen unbound container (total=%d)", len(self._containers))

    # ------------------------------------------------------------------
    # ScreenInterface implementation
    # ------------------------------------------------------------------

    def display_text(self, text: str, **kwargs: Any) -> None:
        self._run_on_loop(self._render_text(text, **kwargs))

    def display_html(self, html: str) -> None:
        self._run_on_loop(self._render_html(html))

    def display_image(self, image_path: str) -> None:
        self._run_on_loop(self._render_image(image_path))

    def display_markdown(self, markdown: str) -> None:
        self._run_on_loop(self._render_markdown(markdown))

    def clear(self) -> None:
        self._run_on_loop(self._render_clear())

    # ------------------------------------------------------------------
    # Async renderers (run on NiceGUI event loop)
    # ------------------------------------------------------------------

    async def _render_text(self, text: str, **kwargs: Any) -> None:
        for container in list(self._containers):
            try:
                container.clear()
                with container:
                    font_size = kwargs.get("font_size", 24)
                    color = kwargs.get("color", "white")
                    bg = kwargs.get("background", "")
                    align = kwargs.get("align", "center")

                    style = f"font-size: {font_size}px; color: {color}; white-space: pre-wrap; "
                    style += f"text-align: {align}; width: 100%; "
                    if bg:
                        style += f"background: {bg}; "
                    ui.html(f'<div style="{style}">{_escape_html(text)}</div>')
            except RuntimeError:
                self._containers.discard(container)

    async def _render_html(self, html: str) -> None:
        for container in list(self._containers):
            try:
                container.clear()
                with container:
                    ui.html(html)
            except RuntimeError:
                self._containers.discard(container)

    async def _render_image(self, image_path: str) -> None:
        for container in list(self._containers):
            try:
                container.clear()
                with container:
                    ui.image(image_path).style("max-width: 100%; max-height: 100%;")
            except RuntimeError:
                self._containers.discard(container)

    async def _render_markdown(self, markdown: str) -> None:
        for container in list(self._containers):
            try:
                container.clear()
                with container:
                    ui.markdown(markdown)
            except RuntimeError:
                self._containers.discard(container)

    async def _render_clear(self) -> None:
        for container in list(self._containers):
            try:
                container.clear()
            except RuntimeError:
                self._containers.discard(container)

    # ------------------------------------------------------------------
    # Thread-safety helper
    # ------------------------------------------------------------------

    def _run_on_loop(self, coro: Any) -> None:
        """Marshal a coroutine to the NiceGUI event loop.

        If called from the event-loop thread, runs inline.
        If called from another thread (e.g. app daemon thread),
        uses ``run_coroutine_threadsafe``.
        """
        if self._loop is None or not self._containers:
            _log.warning("NiceGUIScreen: no loop/containers — call bind_container() first")
            return

        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        if running is self._loop:
            # Already on the NiceGUI loop — just create the task.
            self._loop.create_task(coro)
        else:
            asyncio.run_coroutine_threadsafe(coro, self._loop)


def _escape_html(text: str) -> str:
    """Minimal HTML escape for plain text rendering."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )
