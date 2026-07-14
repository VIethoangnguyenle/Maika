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


def test_rollback_restores_deleted_directory(tmp_path, monkeypatch):
    """A mid-purge failure must roll the whole core back — delete_directory
    actions are backed up and restored, not lost (F10a)."""
    target = tmp_path / "t"
    _write(target, f"{FR}/knowledge/active/note.md", "keep me")
    _write(target, f"{FR}/rules/RULES.md", "framework")
    (tmp_path / "staging").mkdir()
    plan = {"version": 1, "operation": "uninstall-purge", "actions": [
        {"kind": "delete_directory", "path": f"{FR}/knowledge", "ownership": "project",
         "explicit_project_delete": True},
        {"kind": "delete_directory", "path": f"{FR}/rules", "ownership": "framework"},
    ]}
    before = _digest(target)
    # Fail on the applied-persist right after the first directory is deleted.
    monkeypatch.setattr(tx, "_atomic_write", _fail_on(4))
    with pytest.raises(RuntimeError):
        tx.Transaction(tmp_path / "staging", target, tmp_path / "bak").apply(plan)
    assert _digest(target) == before  # both directories restored


def test_dry_run_returns_plan_actions_unchanged(tmp_path):
    staging = _make_staging(tmp_path)
    target = tmp_path / "t"
    plan = build_plan(staging, target, "init", FR)
    journal = tx.Transaction(staging, target, tmp_path / "bak").apply(plan, dry_run=True)
    assert journal["applied"] == []
    assert journal["dry_run"] is True


def test_persists_journal_before_first_target_write_and_commits(tmp_path, monkeypatch):
    staging = _make_staging(tmp_path)
    target = tmp_path / "t"
    plan = build_plan(staging, target, "init", FR)
    real = tx._atomic_write
    observed = {"journal_before_write": False}

    def observing_write(dest, data, mode_src=None):
        if ".maika-transactions/journals" not in dest.as_posix():
            journals = list((target / ".maika-transactions/journals").glob("*.yaml"))
            observed["journal_before_write"] = bool(journals)
        return real(dest, data, mode_src=mode_src)

    monkeypatch.setattr(tx, "_atomic_write", observing_write)
    journal = tx.Transaction(staging, target, tmp_path / "ignored").apply(plan)
    assert observed["journal_before_write"]
    persisted = target / journal["journal_path"]
    assert persisted.is_file()
    import yaml
    assert yaml.safe_load(persisted.read_text(encoding="utf-8"))["status"] == "committed"


def test_repair_restores_an_interrupted_transaction(tmp_path):
    target = tmp_path / "t"
    original = _write(target, "AGENTS.md", "before\n")
    transaction_id = "000001-update"
    backup_path = target / ".maika/runtime/backups" / transaction_id / "AGENTS.md"
    backup_path.parent.mkdir(parents=True)
    backup_path.write_bytes(original.read_bytes())
    original.write_text("after\n", encoding="utf-8")
    journal_path = target / ".maika/runtime/transactions" / f"{transaction_id}.yaml"
    journal_path.parent.mkdir(parents=True)
    import yaml
    journal_path.write_text(yaml.safe_dump({
        "version": 1, "transaction_id": transaction_id, "status": "applying",
        "actions": [{"kind": "replace", "path": "AGENTS.md", "ownership": "shared-host"}],
        "preexisting": {"AGENTS.md": "file"},
    }), encoding="utf-8")

    result = tx.repair_transaction(target, transaction_id)
    assert result["status"] == "rolled_back"
    assert original.read_text(encoding="utf-8") == "before\n"
