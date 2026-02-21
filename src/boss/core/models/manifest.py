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

    name: str = Field(description="Human-friendly app name")
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


# ---------------------------------------------------------------------------
# Legacy migration helper
# ---------------------------------------------------------------------------

# Keys that changed between v2 → v3 manifests.  Mapping is {old_key: new_key}.
_V2_RENAMES: dict[str, str] = {
    # Add entries here when v2 manifests used a different key name.
    # e.g.  "timeout": "timeout_seconds",
}


def migrate_manifest_v2(raw: dict[str, Any]) -> dict[str, Any]:
    """Apply v2 → v3 key renames so old manifests still parse.

    Returns a **new** dict (the input is not mutated).
    """
    out = dict(raw)
    for old_key, new_key in _V2_RENAMES.items():
        if old_key in out and new_key not in out:
            out[new_key] = out.pop(old_key)
    return out
