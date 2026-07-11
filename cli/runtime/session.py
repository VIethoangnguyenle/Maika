"""Compatibility shim — re-exports from session_registry.

The per-session registry (``session_registry.py``) is the implementation.
This module re-exports public names so existing importers keep working.
``SessionConflictError`` is removed — the registry never raises it.
"""

from __future__ import annotations

from cli.runtime.session_registry import (  # noqa: F401
    DEFAULT_STALE_AFTER_SECONDS,
    SESSION_VERSION,
    SessionError,
    TRUSTED_SOURCES,
    record_session,
    resolve_active_platform,
    list_sessions,
    fresh_platforms,
    prune_sessions,
    set_active_platform,
    clear_active_platform,
    load_active_platform,
)
