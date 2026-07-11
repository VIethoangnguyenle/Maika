"""Litmus tests for the transactional install engine.

Any failure mid-apply must restore the exact pre-operation target state: a
recursive hash of the target is identical before and after an injected failure,
host files come back byte-for-byte, and directories the transaction created are
removed when rollback leaves them empty.
"""

import hashlib
from pathlib import Path

import pytest

from cli.install import transaction as tx
from cli.install.planner import build_plan

FR = ".maika"


def _write(root: Path, rel: str, text: str):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _digest(root: Path) -> dict:
    """rel-path -> sha256 of bytes for every file under root (order-independent)."""
    out = {}
    if root.exists():
        for p in sorted(root.rglob("*")):
            if p.is_file():
                out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _fail_on(call_index):
    """Return an _atomic_write replacement that raises on the Nth (1-based) call."""
    state = {"n": 0}
    real = tx._atomic_write

    def wrapper(dest, data, mode_src=None):
        state["n"] += 1
        if state["n"] == call_index:
            raise RuntimeError(f"injected failure on write #{call_index}")
        return real(dest, data, mode_src=mode_src)

    return wrapper


def _make_staging(tmp_path):
    staging = tmp_path / "staging"
    _write(staging, f"{FR}/rules/RULES.md", "rules-new")
    _write(staging, f"{FR}/skills/s/SKILL.md", "skill-new")
    _write(staging, "AGENTS.md", "<!-- maika:begin -->\nblock\n<!-- maika:end -->\n")
    return staging


# ─── happy path ───

def test_apply_writes_all_actions(tmp_path):
    staging = _make_staging(tmp_path)
    target = tmp_path / "t"
    plan = build_plan(staging, target, "init", FR)

    tx.Transaction(staging, target, tmp_path / "bak").apply(plan)

    assert (target / f"{FR}/rules/RULES.md").read_text() == "rules-new"
    assert (target / "AGENTS.md").read_text().startswith("<!-- maika:begin -->")


def test_dry_run_creates_no_files(tmp_path):
    staging = _make_staging(tmp_path)
    target = tmp_path / "t"
    plan = build_plan(staging, target, "init", FR)

    before = _digest(target)
    tx.Transaction(staging, target, tmp_path / "bak").apply(plan, dry_run=True)
    assert _digest(target) == before  # empty → empty; nothing written


# ─── rollback litmus ───

def test_rollback_on_first_action(tmp_path, monkeypatch):
    staging = _make_staging(tmp_path)
    target = tmp_path / "t"
    _write(target, "preexisting.txt", "host")  # untouched bystander
    plan = build_plan(staging, target, "init", FR)

    before = _digest(target)
    monkeypatch.setattr(tx, "_atomic_write", _fail_on(1))
    with pytest.raises(RuntimeError):
        tx.Transaction(staging, target, tmp_path / "bak").apply(plan)
    assert _digest(target) == before


def test_rollback_on_middle_action(tmp_path, monkeypatch):
    staging = _make_staging(tmp_path)
    target = tmp_path / "t"
    plan = build_plan(staging, target, "init", FR)

    before = _digest(target)
    monkeypatch.setattr(tx, "_atomic_write", _fail_on(2))
    with pytest.raises(RuntimeError):
        tx.Transaction(staging, target, tmp_path / "bak").apply(plan)
    assert _digest(target) == before


def test_rollback_on_final_action(tmp_path, monkeypatch):
    staging = _make_staging(tmp_path)
    target = tmp_path / "t"
    plan = build_plan(staging, target, "init", FR)
    n_writes = sum(1 for a in plan["actions"] if a["kind"] != "delete_framework_file")

    before = _digest(target)
    monkeypatch.setattr(tx, "_atomic_write", _fail_on(n_writes))
    with pytest.raises(RuntimeError):
        tx.Transaction(staging, target, tmp_path / "bak").apply(plan)
    assert _digest(target) == before


def test_rollback_restores_existing_host_files_byte_identical(tmp_path, monkeypatch):
    staging = _make_staging(tmp_path)
    _write(staging, ".codex/hooks.json", '{"hooks": "maika-merged"}\n')
    target = tmp_path / "t"
    agents_original = "# Team rules\n\nkeep me\n"
    json_original = '{"team": "keep", "hooks": "old"}\n'
    _write(target, "AGENTS.md", agents_original)
    _write(target, ".codex/hooks.json", json_original)
    plan = build_plan(staging, target, "init", FR)

    before = _digest(target)
    # Fail on the very last write so earlier replaces (AGENTS.md, hooks.json) are
    # applied first, then rolled back.
    n_writes = sum(1 for a in plan["actions"] if a["kind"] != "delete_framework_file")
    monkeypatch.setattr(tx, "_atomic_write", _fail_on(n_writes))
    with pytest.raises(RuntimeError):
        tx.Transaction(staging, target, tmp_path / "bak").apply(plan)

    assert _digest(target) == before
    assert (target / "AGENTS.md").read_text(encoding="utf-8") == agents_original
    assert (target / ".codex" / "hooks.json").read_text(encoding="utf-8") == json_original


def test_rollback_removes_newly_created_empty_dirs(tmp_path, monkeypatch):
    staging = _make_staging(tmp_path)
    target = tmp_path / "t"
    plan = build_plan(staging, target, "init", FR)

    monkeypatch.setattr(tx, "_atomic_write", _fail_on(2))
    with pytest.raises(RuntimeError):
        tx.Transaction(staging, target, tmp_path / "bak").apply(plan)
    # No framework subdirs left behind by the aborted transaction.
    assert not (target / FR).exists()


def test_dry_run_returns_plan_actions_unchanged(tmp_path):
    staging = _make_staging(tmp_path)
    target = tmp_path / "t"
    plan = build_plan(staging, target, "init", FR)
    journal = tx.Transaction(staging, target, tmp_path / "bak").apply(plan, dry_run=True)
    assert journal["applied"] == []
    assert journal["dry_run"] is True
