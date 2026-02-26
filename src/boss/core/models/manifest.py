"""AppManifest Pydantic model — mini-app metadata loaded from ``manifest.json``."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AppManifest(BaseModel):
    """Validated manifest for a single mini-app directory.

    The ``config`` field is explicitly modelled to fix the v2 bug where
    unknown fields (including ``config``) were silently dropped.
    ``extra="forbid"`` ensures any typos or unknown keys raise immediately.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Machine-readable app identifier (must match directory)")
    display_name: str | None = Field(
        default=None,
        description="Human-readable name shown in the UI (auto-derived from *name* when omitted)",
    )
    description: str = Field(default="", description="Short description")
    version: str = Field(default="1.0.0")
    author: str = Field(default="")
    entry_point: str = Field(default="main.py", description="Python file to execute")
    timeout_seconds: int = Field(default=120, ge=1, description="Max run time")
    timeout_behavior: Literal["return"] = Field(
        default="return",
        description="What to do on timeout — 'return' sets stop_event cooperatively",
    )
    requires_network: bool = Field(default=False)
    requires_audio: bool = Field(default=False)
    tags: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="App-specific config passed through to run()",
    )
    required_env: list[str] = Field(
        default_factory=list,
        description="Env-var / secret keys the app needs (validated at scan time)",
    )

    @property
    def effective_display_name(self) -> str:
        """Return *display_name* if set, otherwise title-case the *name* field."""
        if self.display_name:
            return self.display_name
        return self.name.replace("_", " ").title()


# ---------------------------------------------------------------------------
# Legacy migration helper
# ---------------------------------------------------------------------------

# Keys that changed between v2 → v3 manifests.  Mapping is {old_key: new_key}.
_V2_RENAMES: dict[str, str] = {
    # e.g.  "timeout": "timeout_seconds",
}

# Top-level keys to silently strip (present in some v2 manifests but
# forbidden by v3's ``extra="forbid"``).
_V2_STRIP_KEYS: set[str] = {
    "external_apis",
}


def migrate_manifest_v2(raw: dict[str, Any]) -> dict[str, Any]:
    """Apply v2 → v3 key renames so old manifests still parse.

    - Renames legacy keys (see ``_V2_RENAMES``).
    - Strips top-level keys that v3 doesn't recognise (``_V2_STRIP_KEYS``).
    - Maps ``timeout_behavior`` values ``"none"`` / ``"rerun"`` → ``"return"``
      and bumps ``timeout_seconds`` to 900 when appropriate.

    Returns a **new** dict (the input is not mutated).
    """
    out = dict(raw)

    # 1. Rename legacy keys
    for old_key, new_key in _V2_RENAMES.items():
        if old_key in out and new_key not in out:
            out[new_key] = out.pop(old_key)

    # 2. Strip forbidden top-level keys
    for key in _V2_STRIP_KEYS:
        out.pop(key, None)

    # 3. Fix timeout_behavior
    tb = out.get("timeout_behavior", "return")
    if tb in ("none", "rerun"):
        out["timeout_behavior"] = "return"
        # These apps were intended to run indefinitely — give them a generous timeout
        if "timeout_seconds" not in out or out.get("timeout_seconds", 120) < 600:
            out["timeout_seconds"] = 900

    return out
