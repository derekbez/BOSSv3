"""Shared HTTP helpers for network mini-apps.

Provides a resilient ``fetch_json`` wrapper around :mod:`requests` with
automatic retry, backoff, and concise error summarisation.
"""

from __future__ import annotations

import time
from typing import Any

import requests

from boss.apps._lib.error_utils import summarize_error


def fetch_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 6.0,
    retries: int = 1,
    backoff: float = 1.5,
) -> Any:
    """GET *url* and return parsed JSON.

    Args:
        url: Full URL to fetch.
        params: Query-string parameters.
        headers: Extra HTTP headers (``User-Agent`` is always set).
        timeout: Per-request timeout in seconds.
        retries: Number of **additional** attempts after the first failure.
        backoff: Multiplier for sleep between retries (``backoff * attempt``).

    Returns:
        Parsed JSON (dict or list).

    Raises:
        RuntimeError: On exhausted retries or non-JSON responses, with a
            human-readable summary suitable for display.
    """
    hdrs = {"User-Agent": "BOSS-MiniApp/3.0", "Accept": "application/json"}
    if headers:
        hdrs.update(headers)

    last_exc: Exception | None = None
    for attempt in range(1 + retries):
        try:
            resp = requests.get(url, params=params, headers=hdrs, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))

    assert last_exc is not None
    raise RuntimeError(summarize_error(last_exc)) from last_exc


def fetch_text(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 6.0,
) -> str:
    """GET *url* and return the response body as plain text."""
    hdrs = {"User-Agent": "BOSS-MiniApp/3.0"}
    if headers:
        hdrs.update(headers)

    try:
        resp = requests.get(url, params=params, headers=hdrs, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        raise RuntimeError(summarize_error(exc)) from exc
