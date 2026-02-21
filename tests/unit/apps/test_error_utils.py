"""Tests for boss.apps._lib.error_utils."""

from __future__ import annotations

import pytest
from boss.apps._lib.error_utils import summarize_error


class TestSummarizeError:
    def test_generic_exception(self):
        assert summarize_error(ValueError("oops")) == "oops"

    def test_empty_message_uses_class_name(self):
        assert summarize_error(ValueError()) == "ValueError"

    def test_truncation(self):
        msg = "x" * 100
        result = summarize_error(ValueError(msg), max_len=20)
        assert len(result) <= 20
        assert result.endswith("...")

    def test_requests_timeout(self):
        import requests
        err = requests.exceptions.Timeout("timed out")
        assert summarize_error(err) == "Timeout"

    def test_requests_connect_timeout(self):
        import requests
        err = requests.exceptions.ConnectTimeout("connect timed out")
        assert summarize_error(err) == "Connect timeout"

    def test_requests_read_timeout(self):
        import requests
        err = requests.exceptions.ReadTimeout("read timed out")
        assert summarize_error(err) == "Read timeout"

    def test_requests_ssl_error(self):
        import requests
        err = requests.exceptions.SSLError("ssl fail")
        assert summarize_error(err) == "TLS/SSL error"

    def test_requests_too_many_redirects(self):
        import requests
        err = requests.exceptions.TooManyRedirects("too many")
        assert summarize_error(err) == "Too many redirects"

    def test_connection_error_dns(self):
        import requests
        err = requests.exceptions.ConnectionError("Name or service not known")
        assert summarize_error(err) == "DNS failure"

    def test_connection_error_refused(self):
        import requests
        err = requests.exceptions.ConnectionError("Connection refused")
        assert summarize_error(err) == "Connection refused"

    def test_connection_error_generic(self):
        import requests
        err = requests.exceptions.ConnectionError("something else")
        assert summarize_error(err) == "Connection error"
