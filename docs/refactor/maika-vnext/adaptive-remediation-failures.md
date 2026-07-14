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

## Phase 0b — additional Windows-only failures (fixed to reach green)

Fixing the three above let Windows CI progress and reveal further
cross-platform defects (Phase 7 territory, pulled forward because Windows-green
is a hard exit criterion). Each was reproduced locally by simulating Windows
newline translation, except where noted.

```yaml
- test: test_workspace_lock_prevents_duplicate_apply_and_recovers_orphan
  platform: windows-latest
  failure: hang / KeyboardInterrupt in microloop group
  root_cause: WorkspaceLock._orphaned used os.kill(pid, 0) for liveness; on
    Windows os.kill with a non-CTRL signal calls TerminateProcess (wrong AND
    destructive).
  fix: _process_alive(pid) — POSIX os.kill(pid,0), Windows OpenProcess query;
    never signals the target.

- test: test_vnext_cli_e2e worker-dispatch tests
  platform: windows-latest
  failure: mangled prompt / hang under cmd.exe
  root_cause: worker runner used shell=True + shlex.quote(prompt) (POSIX-only).
  fix: structured worker {executable, args:[...]}; prompt passed via argv
    (shell=False), placeholder validation, {prompt_file} option.

- test: test_run_queue_* (several)
  platform: windows-latest
  failure: "stale capsule" -> tasks blocked instead of done
  root_cause: _dump_yaml wrote text mode via os.fdopen(fd,"w") -> CRLF on disk;
    read_bytes()-based evidence_sha diverged from read_text()-based gate hash.
  fix: _dump_yaml writes newline="" (byte-identical LF everywhere).

- test: test_review_plan_approved
  platform: windows-latest
  failure: (1) FINDINGS not APPROVED, then (2) UnicodeDecodeError
  root_cause: (1) an absolute OS-path Counter-evidence anchor embedded Windows
    backslashes that the posix _FILE_PATH regex could not extract; (2) the
    review body's non-ASCII em dash was written cp1252 (no encoding=) then read
    utf-8.
  fix: repo-relative posix anchor + write_text(..., encoding="utf-8").

- test: test_public_small_happy_path_completes_with_one_worker_call
  platform: windows-latest
  failure: "a lightweight verification command failed"
  root_cause: validate_command matched executables by basename; sys.executable
    on Windows is "python.exe", absent from the python/python3 allowlist.
  fix: strip only real executable extensions (.exe/.bat/.cmd/.com) so
    python.exe matches python while python.py stays denied (gate not weakened).

- test: rule-projector group (test_checkstyle golden, projector reads)
  platform: windows-latest (pre-emptively fixed; group had not yet run)
  root_cause: projector.py/checkstyle.py + fixture reads used the platform
    default encoding on non-ASCII (Vietnamese DNA, em-dash XML).
  fix: encoding="utf-8" at those sites + .gitattributes ("* text=auto eol=lf").
```

## Result

CI run 29131746554: tests (ubuntu-latest) ✓, tests (windows-latest) ✓,
install-ps1-e2e ✓. Finding 2.9 (CI red) resolved.

## Anticipated siblings still open (tracked for later phases)

```yaml
- location: vnext_dispatch.py:290, cli/knowledge_control.py:401, cli/dashboard/brain.py:195
  pattern: str(path.relative_to(...))  # POSIX-path; not on any Windows CI path today
- location: runtime_hardening.execute_command
  pattern: start_new_session/os.killpg POSIX-only (only trips on worker timeout) — Phase 7-rest
- location: runtime_hardening.parse_review, gates.py front-matter
  pattern: literal "\n" fence; today all reviews are read via read_text (normalized) — defensive
           CRLF normalization deferred to Phase 7-rest
- location: cli/commands/skill.py:20
  pattern: shell=True on agent-authored candidate strings — Phase 7-rest / Phase 3
```

## Policy for changing tests (plan §4.3)

Tests were changed only where the test itself was under-specified for
cross-platform execution (missing `encoding="utf-8"`). No test expectation was
relaxed to legitimize incorrect runtime behavior. In particular the
`blocked -> exit 0` expectation in test_vnext_cli_e2e.py is **not** touched here;
it is corrected in Phase 4 together with the exit-code contract change.
