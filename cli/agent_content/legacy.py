"""Legacy active-memory handling (agent-facing refactor PR 6).

Two mechanical consumers of the ``deprecated`` list in artifact-authority.yaml:

- ``scan_legacy_references`` — flags agent-facing content (rules, procedures,
  workflows, skills, agent kernel, knowledge README/templates) that still
  references a deprecated legacy artifact. Kept clean by CI.
- ``plan_legacy_migration`` / ``apply_legacy_migration`` — migrates a target's
  ``knowledge/active`` legacy files into the canonical ``changes/<id>``
  workspace (SSOT plan §23.1). Never deletes: discarded artifacts move to
  ``archive/legacy-active-import/``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

SCAN_DIRS = ("rules", "procedures", "workflows", "skills", "agent")
SCAN_FILES = ("knowledge/README.md",)
# Path-ish tokens derived from the registry's deprecated entries.
LEGACY_TOKENS = (
    "REQUIREMENT.md",
    "EXPLORE_CONTEXT",
    "AGENT_TRANSPARENCY",
    "TOKEN_LOG",
    "active/ideation",
    "knowledge/active/BOOTSTRAP_REPORT",
)
ARCHIVE_IMPORT_DIR = "legacy-active-import"


def scan_legacy_references(framework_dir: Path) -> list[dict]:
    framework_dir = Path(framework_dir)
    findings: list[dict] = []
    files: list[Path] = []
    for rel in SCAN_DIRS:
        root = framework_dir / rel
        if root.exists():
            files.extend(sorted(root.rglob("*.md")))
    files.extend(framework_dir / rel for rel in SCAN_FILES if (framework_dir / rel).exists())
    for path in files:
        rel_path = path.relative_to(framework_dir).as_posix()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for token in LEGACY_TOKENS:
                if token in line:
                    findings.append({"file": rel_path, "line": lineno, "token": token})
    templates = framework_dir / "knowledge" / "templates"
    if templates.exists():
        for path in sorted(templates.iterdir()):
            for token in LEGACY_TOKENS:
                if token.split("/")[-1].split(".")[0] in path.name:
                    findings.append({"file": path.relative_to(framework_dir).as_posix(),
                                     "line": 0, "token": f"template file ({token})"})
    return findings


def _single_active_change(framework_dir: Path) -> Path | None:
    changes = framework_dir / "changes"
    if not changes.exists():
        return None
    active = sorted(p.parent for p in changes.glob("*/STATE.yaml"))
    return active[0] if len(active) == 1 else None


def plan_legacy_migration(framework_dir: Path) -> list[dict]:
    framework_dir = Path(framework_dir)
    active_dir = framework_dir / "knowledge" / "active"
    ws = _single_active_change(framework_dir)
    archive_import = framework_dir / "archive" / ARCHIVE_IMPORT_DIR
    moves: list[dict] = []

    def _plan(source: Path, target: Path, note: str) -> None:
        if source.exists():
            moves.append({"source": source, "target": target, "note": note})

    if ws is not None:
        intent = ws / "INTENT.md"
        _plan(active_dir / "REQUIREMENT.md",
              intent if not intent.exists() else ws / "INTENT.legacy.md",
              "requirement -> intent")
        _plan(active_dir / "EXPLORE_CONTEXT.md", ws / "exploration" / "LEGACY_IMPORT.md",
              "explore-context -> exploration import")
        _plan(active_dir / "AGENT_TRANSPARENCY.md",
              ws / "generated" / "LEGACY_EVENT_LOG.md",
              "transparency -> legacy event log")
    else:
        for name in ("REQUIREMENT.md", "EXPLORE_CONTEXT.md", "AGENT_TRANSPARENCY.md"):
            _plan(active_dir / name, archive_import / name,
                  "no single active change; archived")
    _plan(active_dir / "TOKEN_LOG.md", archive_import / "TOKEN_LOG.md",
          "discarded (no successor)")
    ideation = active_dir / "ideation"
    if ideation.exists() and any(ideation.iterdir()):
        moves.append({"source": ideation, "target": archive_import / "ideation",
                      "note": "ideation archived"})
    return moves


def apply_legacy_migration(moves: list[dict]) -> list[dict]:
    applied = []
    for move in moves:
        target: Path = move["target"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(move["source"]), str(target))
        applied.append(move)
    return applied
