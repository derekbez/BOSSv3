"""Shared network utilities for mini-apps."""

from __future__ import annotations

import socket


def get_local_ip() -> str:
    """Return the best-effort local IP address, or ``'localhost'`` on failure."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "localhost"
