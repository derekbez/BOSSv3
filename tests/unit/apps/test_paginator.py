"""Tests for boss.apps._lib.paginator."""

from __future__ import annotations

import pytest
from boss.apps._lib.paginator import TextPaginator, wrap_plain, wrap_events, wrap_with_prefix


class TestWrapPlain:
    def test_short_text(self):
        assert wrap_plain("hello", 80) == ["hello"]

    def test_wraps_long_text(self):
        lines = wrap_plain("a " * 50, 20)
        assert len(lines) > 1
        assert all(len(line) <= 20 for line in lines)

    def test_empty_text_returns_itself(self):
        assert wrap_plain("", 80) == [""]


class TestWrapWithPrefix:
    def test_single_line(self):
        result = wrap_with_prefix("short", ">> ", 80)
        assert result == [">> short"]

    def test_wraps_with_indent(self):
        result = wrap_with_prefix("a " * 30, ">> ", 20)
        assert result[0].startswith(">> ")
        assert all(line.startswith("   ") for line in result[1:])


class TestWrapEvents:
    def test_basic(self):
        events = [("1969", "Moon landing"), ("1776", "Declaration signed")]
        result = wrap_events(events, 80)
        assert any("1969" in line for line in result)
        assert any("1776" in line for line in result)


class TestTextPaginator:
    def test_empty_lines(self):
        p = TextPaginator([], per_page=5)
        assert p.total_pages == 1
        assert p.page_lines() == []
        assert not p.has_prev()
        assert not p.has_next()

    def test_single_page(self):
        p = TextPaginator(["a", "b", "c"], per_page=5)
        assert p.total_pages == 1
        assert p.page_lines() == ["a", "b", "c"]
        assert not p.has_next()
        assert not p.has_prev()

    def test_multiple_pages(self):
        lines = [str(i) for i in range(10)]
        p = TextPaginator(lines, per_page=3)
        assert p.total_pages == 4
        assert p.page_lines() == ["0", "1", "2"]
        assert p.has_next()
        assert not p.has_prev()

    def test_navigation(self):
        lines = [str(i) for i in range(6)]
        p = TextPaginator(lines, per_page=3)
        assert p.next()
        assert p.page == 1
        assert p.page_lines() == ["3", "4", "5"]
        assert p.has_prev()
        assert not p.has_next()
        assert p.prev()
        assert p.page == 0

    def test_prev_at_start_returns_false(self):
        p = TextPaginator(["a"], per_page=5)
        assert not p.prev()

    def test_next_at_end_returns_false(self):
        p = TextPaginator(["a"], per_page=5)
        assert not p.next()

    def test_set_lines(self):
        p = TextPaginator(["a"], per_page=5)
        p.set_lines(["x", "y", "z"])
        assert p.page_lines() == ["x", "y", "z"]

    def test_reset(self):
        lines = [str(i) for i in range(10)]
        p = TextPaginator(lines, per_page=3)
        p.next()
        p.next()
        p.reset()
        assert p.page == 0

    def test_led_callback(self):
        calls: list[tuple[str, bool]] = []
        p = TextPaginator(
            [str(i) for i in range(6)],
            per_page=3,
            led_update=lambda c, on: calls.append((c, on)),
        )
        # Initial state: no prev, has next
        assert ("yellow", False) in calls
        assert ("blue", True) in calls
        calls.clear()
        p.next()
        assert ("yellow", True) in calls
        assert ("blue", False) in calls
