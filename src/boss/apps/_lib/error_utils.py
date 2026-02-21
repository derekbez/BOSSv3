"""Shared error summarization for network mini-apps.

Converts raw ``requests`` exceptions into concise, user-friendly messages
suitable for display on the BOSS screen.
"""

from __future__ import annotations


def summarize_error(err: Exception, max_len: int = 60) -> str:
    """Return a concise human-readable summary for a network exception."""
    try:
        import requests  # type: ignore[import-untyped]
    except ImportError:
        # If requests isn't available, fall back to generic string
        raw = str(err) or err.__class__.__name__
        return raw[:max_len]

    if isinstance(err, requests.exceptions.ConnectTimeout):
        msg = "Connect timeout"
    elif isinstance(err, requests.exceptions.ReadTimeout):
        msg = "Read timeout"
    elif isinstance(err, requests.exceptions.Timeout):
        msg = "Timeout"
    elif isinstance(err, requests.exceptions.SSLError):
        msg = "TLS/SSL error"
    elif isinstance(err, requests.exceptions.TooManyRedirects):
        msg = "Too many redirects"
    elif isinstance(err, requests.exceptions.HTTPError):
        resp = getattr(err, "response", None)
        if resp is not None:
            reason = getattr(resp, "reason", "") or ""
            msg = f"HTTP {resp.status_code} {reason}".strip()
        else:
            msg = "HTTP error"
    elif isinstance(err, requests.exceptions.ConnectionError):
        raw = str(err)
        if "Name or service not known" in raw or "Temporary failure" in raw:
            msg = "DNS failure"
        elif "Failed to establish" in raw or "NewConnectionError" in raw:
            msg = "Connection failed"
        elif "Connection refused" in raw:
            msg = "Connection refused"
        else:
            msg = "Connection error"
    else:
        raw = str(err) or err.__class__.__name__
        if "Max retries exceeded" in raw:
            if "Read timed out" in raw:
                msg = "Read timeout"
            elif "Connect timeout" in raw:
                msg = "Connect timeout"
            else:
                msg = "Max retries (network)"
        else:
            msg = raw

    if len(msg) > max_len:
        msg = msg[: max_len - 3] + "..."
    return msg
