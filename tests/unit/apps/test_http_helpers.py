"""Tests for boss.apps._lib.http_helpers."""

from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest

from boss.apps._lib.http_helpers import fetch_json, fetch_text


class TestFetchJson:
    @patch("boss.apps._lib.http_helpers.requests.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"key": "value"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_json("https://example.com/api")
        assert result == {"key": "value"}
        mock_get.assert_called_once()

    @patch("boss.apps._lib.http_helpers.requests.get")
    def test_passes_params_and_headers(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        fetch_json(
            "https://example.com/api",
            params={"q": "test"},
            headers={"X-Key": "abc"},
            timeout=3.0,
        )
        _, kwargs = mock_get.call_args
        assert kwargs["params"] == {"q": "test"}
        assert kwargs["timeout"] == 3.0
        assert kwargs["headers"]["X-Key"] == "abc"
        assert "User-Agent" in kwargs["headers"]

    @patch("boss.apps._lib.http_helpers.requests.get")
    def test_retries_on_failure(self, mock_get):
        import requests as req

        mock_get.side_effect = [
            req.exceptions.ReadTimeout("timeout"),
            MagicMock(
                json=MagicMock(return_value={"ok": True}),
                raise_for_status=MagicMock(),
            ),
        ]
        result = fetch_json("https://example.com", retries=1, backoff=0.01)
        assert result == {"ok": True}
        assert mock_get.call_count == 2

    @patch("boss.apps._lib.http_helpers.requests.get")
    def test_raises_after_retries_exhausted(self, mock_get):
        import requests as req

        mock_get.side_effect = req.exceptions.ConnectTimeout("fail")
        with pytest.raises(RuntimeError, match="Connect timeout"):
            fetch_json("https://example.com", retries=1, backoff=0.01)
        assert mock_get.call_count == 2


class TestFetchText:
    @patch("boss.apps._lib.http_helpers.requests.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = "<xml>data</xml>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_text("https://example.com")
        assert result == "<xml>data</xml>"

    @patch("boss.apps._lib.http_helpers.requests.get")
    def test_raises_on_error(self, mock_get):
        import requests as req

        mock_get.side_effect = req.exceptions.ConnectionError("fail")
        with pytest.raises(RuntimeError):
            fetch_text("https://example.com")
