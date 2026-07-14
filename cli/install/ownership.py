"""Ownership classification for install actions.

Three ownership classes decide how the transaction engine may touch a target
path (see the multi-framework plan §3.2):

- framework   — Maika-owned; freely created/replaced/deleted by update.
- project     — user data; created when absent, never replaced or deleted.
- shared-host — host files Maika only merges a namespaced block/entry into.
"""

from __future__ import annotations

from pathlib import PurePosixPath

FRAMEWORK = "framework"
PROJECT = "project"
SHARED_HOST = "shared-host"

# Host files Maika co-owns via a managed block (markdown) or namespaced entry
# (json); everything outside the managed region is preserved.
_SHARED_HOST = frozenset({
    "AGENTS.md",
    "CLAUDE.md",
    ".claude/settings.json",
    ".codex/hooks.json",
    ".agents/hooks.json",
})

# Project-owned top-level subtrees under the framework root — user state.
_PROJECT_TOP = frozenset({"changes", "archive", "loops", "reports"})

# Project-owned knowledge subtrees (user seeds/data). knowledge/templates and
# knowledge/README.md are framework-shipped and refreshed on update.
_PROJECT_KNOWLEDGE = (
    "knowledge/active", "knowledge/long-term", "knowledge/skill-evolution",
    "knowledge/preferences",
)

# Framework-generated files that live inside a project subtree but are
# regenerated every run (so they are replaceable, not preserved).
_GENERATED_IN_PROJECT = frozenset({"knowledge/long-term/knowledge-index.yaml"})


def classify(rel_path: str, framework_root: str = ".maika") -> str:
    """Classify a repo-relative path into an ownership class."""
    rel = PurePosixPath(rel_path).as_posix()
    if rel in _SHARED_HOST:
        return SHARED_HOST

    fr = framework_root.rstrip("/")
    parts = PurePosixPath(rel).parts
    if not (len(parts) >= 2 and parts[0] == fr):
        return FRAMEWORK

    under_fr = "/".join(parts[1:])
    if under_fr in _GENERATED_IN_PROJECT:
        return FRAMEWORK
    if under_fr == "config/project.local.yaml":
        return PROJECT
    if parts[1] in _PROJECT_TOP:
        return PROJECT
    for subtree in _PROJECT_KNOWLEDGE:
        if under_fr == subtree or under_fr.startswith(subtree + "/"):
            return PROJECT
    return FRAMEWORK
