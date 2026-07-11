"""Tests for the install planner and ownership classification.

The planner turns a fully-staged desired tree + the current target into a pure
data action list — no side effects. Ownership drives which paths may be
replaced (framework/shared-host) and which are preserved (project).
"""

from pathlib import Path

from cli.install import ownership
from cli.install.planner import build_plan

FR = ".maika"


def _write(root: Path, rel: str, text: str = "x"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _by_path(plan):
    return {a["path"]: a for a in plan["actions"]}


# ─── ownership ───

def test_ownership_shared_host_entrypoints_and_configs():
    assert ownership.classify("AGENTS.md", FR) == ownership.SHARED_HOST
    assert ownership.classify("CLAUDE.md", FR) == ownership.SHARED_HOST
    assert ownership.classify(".claude/settings.json", FR) == ownership.SHARED_HOST
    assert ownership.classify(".codex/hooks.json", FR) == ownership.SHARED_HOST


def test_ownership_project_knowledge_is_preserved():
    assert ownership.classify(f"{FR}/knowledge/long-term/author-dna.yaml", FR) == ownership.PROJECT
    assert ownership.classify(f"{FR}/changes/C-1/CHANGE.yaml", FR) == ownership.PROJECT


def test_ownership_generated_knowledge_index_is_framework():
    # Regenerated every run — framework-owned even though it lives in the
    # project knowledge subtree.
    assert ownership.classify(f"{FR}/knowledge/long-term/knowledge-index.yaml", FR) == ownership.FRAMEWORK


def test_ownership_framework_default():
    assert ownership.classify(f"{FR}/rules/RULES.md", FR) == ownership.FRAMEWORK
    assert ownership.classify(f"{FR}/resolved-config.yaml", FR) == ownership.FRAMEWORK


# ─── planner ───

def test_plan_create_vs_replace(tmp_path):
    staging, target = tmp_path / "s", tmp_path / "t"
    _write(staging, f"{FR}/rules/RULES.md")
    _write(staging, f"{FR}/rules/new.md")
    _write(target, f"{FR}/rules/RULES.md", "old")  # exists → replace

    actions = _by_path(build_plan(staging, target, "init", FR))
    assert actions[f"{FR}/rules/RULES.md"]["kind"] == "replace"
    assert actions[f"{FR}/rules/new.md"]["kind"] == "create"


def test_plan_shared_host_kinds(tmp_path):
    staging, target = tmp_path / "s", tmp_path / "t"
    _write(staging, "AGENTS.md")
    _write(staging, ".codex/hooks.json")

    actions = _by_path(build_plan(staging, target, "init", FR))
    assert actions["AGENTS.md"]["kind"] == "managed_markdown"
    assert actions["AGENTS.md"]["ownership"] == ownership.SHARED_HOST
    assert actions[".codex/hooks.json"]["kind"] == "merge_json"


def test_plan_preserves_existing_project_owned(tmp_path):
    staging, target = tmp_path / "s", tmp_path / "t"
    _write(staging, f"{FR}/knowledge/long-term/author-dna.yaml", "seed")
    _write(target, f"{FR}/knowledge/long-term/author-dna.yaml", "user-edited")

    actions = _by_path(build_plan(staging, target, "update", FR))
    # Project-owned + already present → no action (never clobber user data).
    assert f"{FR}/knowledge/long-term/author-dna.yaml" not in actions


def test_plan_creates_absent_project_owned(tmp_path):
    staging, target = tmp_path / "s", tmp_path / "t"
    _write(staging, f"{FR}/knowledge/long-term/author-dna.yaml", "seed")

    actions = _by_path(build_plan(staging, target, "init", FR))
    assert actions[f"{FR}/knowledge/long-term/author-dna.yaml"]["kind"] == "create"


def test_plan_update_deletes_framework_orphans(tmp_path):
    staging, target = tmp_path / "s", tmp_path / "t"
    _write(staging, f"{FR}/rules/RULES.md")
    # Orphan: a framework file present in target's managed dir but not staged.
    _write(target, f"{FR}/rules/RULES.md", "old")
    _write(target, f"{FR}/rules/legacy.md", "dropped")

    actions = _by_path(build_plan(staging, target, "update", FR))
    assert actions[f"{FR}/rules/legacy.md"]["kind"] == "delete_framework_file"


def test_plan_init_does_not_delete_orphans(tmp_path):
    staging, target = tmp_path / "s", tmp_path / "t"
    _write(staging, f"{FR}/rules/RULES.md")
    _write(target, f"{FR}/rules/legacy.md", "kept")

    kinds = {a["kind"] for a in build_plan(staging, target, "init", FR)["actions"]}
    assert "delete_framework_file" not in kinds


def test_plan_is_pure_data_no_writes(tmp_path):
    staging, target = tmp_path / "s", tmp_path / "t"
    _write(staging, f"{FR}/rules/RULES.md")
    before = {p for p in target.rglob("*")} if target.exists() else set()
    build_plan(staging, target, "init", FR)
    after = {p for p in target.rglob("*")} if target.exists() else set()
    assert before == after  # planner mutates nothing
