"""In-memory screen implementation for testing.

Stores the last rendered content so tests can assert on it without
requiring NiceGUI or any UI event loop.
"""

from __future__ import annotations

from boss.core.interfaces.hardware import ScreenInterface


class InMemoryScreen(ScreenInterface):
    """A lightweight screen that records calls in memory.

    Attributes:
        last_text: The last text passed to :meth:`display_text`, or ``None``.
        last_text_kwargs: The last ``**kwargs`` from :meth:`display_text`.
        last_html: The last HTML string passed to :meth:`display_html`.
        last_image: The last image path passed to :meth:`display_image`.
        last_markdown: The last markdown passed to :meth:`display_markdown`.
        cleared: ``True`` after :meth:`clear` is called (reset on next render).
        call_log: Ordered list of ``(method_name, args)`` tuples.
    """

    def __init__(self) -> None:
        self.last_text: str | None = None
        self.last_text_kwargs: dict[str, object] = {}
        self.last_html: str | None = None
        self.last_image: str | None = None
        self.last_markdown: str | None = None
        self.cleared: bool = False
        self.call_log: list[tuple[str, dict[str, object]]] = []

    def display_text(self, text: str, **kwargs: object) -> None:
        self.last_text = text
        self.last_text_kwargs = kwargs
        self.cleared = False
        self.call_log.append(("display_text", {"text": text, **kwargs}))

    def display_html(self, html: str) -> None:
        self.last_html = html
        self.cleared = False
        self.call_log.append(("display_html", {"html": html}))

    def display_image(self, image_path: str) -> None:
        self.last_image = image_path
        self.cleared = False
        self.call_log.append(("display_image", {"image_path": image_path}))

    def display_markdown(self, markdown: str) -> None:
        self.last_markdown = markdown
        self.cleared = False
        self.call_log.append(("display_markdown", {"markdown": markdown}))

    def clear(self) -> None:
        self.last_text = None
        self.last_text_kwargs = {}
        self.last_html = None
        self.last_image = None
        self.last_markdown = None
        self.cleared = True
        self.call_log.append(("clear", {}))
