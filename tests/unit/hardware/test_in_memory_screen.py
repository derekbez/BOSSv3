"""Unit tests for InMemoryScreen."""

from __future__ import annotations

from boss.hardware.mock.mock_screen import InMemoryScreen


class TestInMemoryScreen:
    """InMemoryScreen stores rendered content for assertions."""

    def test_display_text_stores_content(self) -> None:
        screen = InMemoryScreen()
        screen.display_text("Hello", font_size=32, color="red")
        assert screen.last_text == "Hello"
        assert screen.last_text_kwargs == {"font_size": 32, "color": "red"}
        assert screen.cleared is False

    def test_display_html_stores_content(self) -> None:
        screen = InMemoryScreen()
        screen.display_html("<b>Bold</b>")
        assert screen.last_html == "<b>Bold</b>"

    def test_display_image_stores_path(self) -> None:
        screen = InMemoryScreen()
        screen.display_image("/tmp/cat.png")
        assert screen.last_image == "/tmp/cat.png"

    def test_display_markdown_stores_content(self) -> None:
        screen = InMemoryScreen()
        screen.display_markdown("# Title")
        assert screen.last_markdown == "# Title"

    def test_clear_resets_all(self) -> None:
        screen = InMemoryScreen()
        screen.display_text("Hello")
        screen.display_html("<b>Bold</b>")
        screen.display_image("/img.png")
        screen.display_markdown("# Hi")

        screen.clear()
        assert screen.last_text is None
        assert screen.last_html is None
        assert screen.last_image is None
        assert screen.last_markdown is None
        assert screen.cleared is True

    def test_clear_flag_resets_on_next_render(self) -> None:
        screen = InMemoryScreen()
        screen.clear()
        assert screen.cleared is True
        screen.display_text("After clear")
        assert screen.cleared is False

    def test_call_log_records_all_calls(self) -> None:
        screen = InMemoryScreen()
        screen.display_text("A")
        screen.display_html("<b>B</b>")
        screen.clear()
        screen.display_image("/c.png")

        assert len(screen.call_log) == 4
        assert screen.call_log[0][0] == "display_text"
        assert screen.call_log[1][0] == "display_html"
        assert screen.call_log[2][0] == "clear"
        assert screen.call_log[3][0] == "display_image"
