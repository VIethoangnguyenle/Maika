# Adaptive Remediation — CI Failure Inventory (Phase 0)

> Baseline captured from PR #47 (`refactor/maika-vnext-full`), CI run `29128347864`.
> Local Linux (`python scripts/run_ci.py`) was **green** (729 passed, 1 skipped); the
> red CI was caused by an undeclared test dependency (both platforms) plus two
> Windows-only bugs. Windows cannot be reproduced locally, so the RED signal for the
> platform-specific items is the GitHub Actions Windows job itself.

## Confirmed failures (fixed in Phase 0)

```yaml
- test: .maika/tools/rule-projector/tests/test_schema.py (collection)
  platform: ubuntu-latest + windows-latest
  failure: "ModuleNotFoundError: No module named 'jsonschema' -> pytest exit code 2"
  root_cause: >-
    CI installs a fresh `pip install -e . pytest`. `jsonschema` is imported by
    test_schema.py but was never declared as a dependency; local runs passed only
    because the system interpreter happened to have it. Ubuntu stops here (group 6);
    Windows never reaches it because it fails earlier at group 3.
  production_impact: none (test-only dependency)
  fix: >-
    Declared `[project.optional-dependencies].test = ["pytest", "jsonschema>=4.0"]`
    in pyproject.toml and switched CI install to `pip install -e ".[test]"`.
    NOT solved by pytest.importorskip — that would silently hide the schema test
    (the "make it green by weakening" anti-pattern, plan §4.3).
  regression_test: existing test_schema.py now collects on a clean env; CI install step

- test: .maika/tools/microloop-orchestrator/tests/test_plan_compiler.py::test_compile_writes_queue_and_briefs
  platform: windows-latest
  failure: "AssertionError: sha256(body) != stored brief_hash"
  root_cause: >-
    TEST bug, not production. Line 109 read the brief with `read_text()` and no
    encoding. On Windows the default locale encoding is cp1252, which corrupts the
    non-ASCII body ("Thân task 1.") that was written as utf-8, so the recomputed
    hash diverges. Verified by decoding utf-8 bytes as cp1252 -> different sha256.
    The capsule-hash assertion in the same file passed because it used
    `read_text(encoding="utf-8")`.
  production_impact: >-
    none — plan_compiler writes and hashes utf-8 consistently; the defect was in
    the test's read path only.
  fix: read with `encoding="utf-8"` and hash `body.encode("utf-8")` (test line 109-111).
  regression_test: same test, now encoding-correct; passes on Linux + Windows.

- test: .maika/tools/microloop-orchestrator/tests/test_plan_compiler.py::test_compile_writes_knowledge_capsule
  platform: windows-latest
  failure: "AssertionError: 'briefs\\\\TASK-001.knowledge.yaml' == 'briefs/TASK-001.knowledge.yaml'"
  root_cause: >-
    PRODUCTION bug. plan_compiler stored artifact paths with
    `str(path.relative_to(ws))`, which yields OS-native separators (backslash on
    Windows). The write-gate later compares targets via `.as_posix()`, so a
    backslash-stored path would never match declared scope on Windows.
  production_impact: >-
    HIGH on Windows — write-gate scope checks and queue path lookups would fail for
    every task because stored paths used backslashes while the gate compares POSIX.
  fix: >-
    Store brief_path / capsule_path / context_package_path / loaded_artifacts with
    `.relative_to(ws).as_posix()` (plan_compiler.py).
  regression_test: >-
    test_compile_writes_queue_and_briefs now asserts no "\\" in brief_path,
    capsule_path, context_package_path, result_path (green on Linux; the RED for
    this invariant is the Windows CI job).
```

## Anticipated Windows siblings (deferred to Phase 7 cross-platform sweep)

Not fixed in Phase 0 to keep the change surgical; recorded so they are not lost.
Windows CI advancing past group 3 may surface these:

```yaml
- location: .maika/tools/microloop-orchestrator/vnext_dispatch.py:290
  pattern: str(update_path.relative_to(ws))          # same POSIX-path bug class
- location: cli/knowledge_control.py:401
  pattern: str(path.relative_to(long_term))
- location: cli/dashboard/brain.py:195
  pattern: str(path.relative_to(parent))
- location: .maika/tools/rule-projector/{projector.py,backends/checkstyle.py}
  pattern: read_text()/write_text() without encoing on possibly-non-ASCII payloads
- location: worker runner + review parser
  pattern: shell=True/shlex.quote (orchestrator.py), literal "\n" front-matter parse
           (runtime_hardening.parse_review, gates.py) — Phase 7.
```

## Policy for changing tests (plan §4.3)

Tests were changed only where the test itself was under-specified for
cross-platform execution (missing `encoding="utf-8"`). No test expectation was
relaxed to legitimize incorrect runtime behavior. In particular the
`blocked -> exit 0` expectation in test_vnext_cli_e2e.py is **not** touched here;
it is corrected in Phase 4 together with the exit-code contract change.
