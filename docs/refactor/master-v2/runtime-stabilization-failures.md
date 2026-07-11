# Runtime stabilization — CI failure inventory (Phase 0)

Baseline audited: `master-v2` at `8b9448b4d5ed6bf8abefa402c933410a2071ff0c`.

Local reproduction host: Linux. The full Ubuntu-equivalent suite (`python
scripts/run_ci.py`) is **green locally** — 923 tests pass, artifact audit clean.
The failures the plan targets are Windows / PowerShell-specific. GitHub Actions
run logs for the Windows jobs are not fetchable from this host, so this
inventory records what is **statically reproducible** here and flags what still
requires the actual Windows runner.

## Schema

Each entry: `job / test / platform / failure / root_cause / production_impact /
fix / regression_test`.

## F1 — install-ps1-e2e asserts the legacy write-gate filename

```yaml
job: install-ps1-e2e
test: "Assert Windows-rendered artifacts" step (.github/workflows/ci.yml)
platform: windows-latest (pwsh)
failure: >
  throw "write-gate hook command missing" — the step ran
  `if ($settings -notmatch 'write_gate\.py') { throw ... }` against the freshly
  rendered .claude/settings.json.
root_cause: >
  The host-hook contract moved from a hard-coded `python .../write_gate.py`
  line to the OS-agnostic command `maika hook write-gate --runtime <r>
  --platform <p>` (id `maika.write-gate.v1`). The rendered settings.json no
  longer contains the substring `write_gate.py`, so the `-notmatch` guard is
  always true on a correct install and throws.
production_impact: >
  A correct, current install fails the release gate on Windows. The assertion
  no longer describes the shipped artifact, so it cannot catch a real
  regression either — it is both a false failure and a blind spot.
fix: >
  Replace the filename assertion with three canonical-contract assertions in
  the same step: settings must match `maika\.write-gate\.v1`,
  `maika hook write-gate`, and `--platform claude-code`. The adjacent Unix-leak
  and canonical-runtime-profile assertions are unchanged.
regression_test: >
  cli/tests/test_ci_workflow.py::test_install_e2e_asserts_canonical_write_gate_contract
  — fails on the stale ci.yml (asserts the canonical command/id/platform are
  present and the legacy `write_gate.py` filename is absent).
```

## CI trigger coverage (Phase 0 task 4)

```yaml
job: (workflow trigger, not a test)
platform: all
failure: >
  ci.yml only triggered on push to `main` and on pull_request; direct pushes to
  the `master-v2` stabilization branch did not run the matrix, so Windows/Linux
  behavior on the branch was unproven until PR time.
fix: push.branches changed from [main] to [main, master-v2] for the
  stabilization window.
regression_test: >
  cli/tests/test_ci_workflow.py::test_ci_runs_on_stabilization_branch
```

## Open item — remaining `tests` job (windows-latest) failures

```yaml
job: tests (windows-latest)
platform: windows-latest
failure: not reproducible on this Linux host
root_cause: unknown — requires the actual Windows runner
production_impact: unknown until enumerated
status: >
  The Ubuntu-equivalent suite is green locally. A static scan of non-test CLI
  code found no Windows-fatal patterns (no os.fork/SIGKILL/symlink/exec-bit
  reliance; the only `/usr/bin/env` hits are harmless shebang lines). Any
  Windows `tests`-job failure beyond F1 must be captured from a real Windows CI
  run — with ci.yml now triggering on master-v2, the next push produces those
  logs. Do NOT weaken assertions to make the matrix green; capture the log,
  add a row here, then fix root cause with a regression test (plan §4 task 5).
```
