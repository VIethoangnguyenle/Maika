"""Cross-platform worker runner (plan Phase 7): shell=False, structured argv,
prompt passed verbatim (no shell quoting), optional prompt-file, placeholder
validation. These run on POSIX and Windows CI without shlex.quote/shell=True."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import orchestrator as orch


def _record_arg_worker(tmp_path):
    """Worker that copies its prompt argument (argv[2]) to a file (argv[1])."""
    w = tmp_path / "record_arg_worker.py"
    w.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "Path(sys.argv[1]).write_text(sys.argv[2], encoding='utf-8')\n",
        encoding="utf-8",
    )
    return w


def _record_file_worker(tmp_path):
    """Worker that copies the *contents* of its prompt-file (argv[2]) to a file (argv[1])."""
    w = tmp_path / "record_file_worker.py"
    w.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "Path(sys.argv[1]).write_text(Path(sys.argv[2]).read_text(encoding='utf-8'), encoding='utf-8')\n",
        encoding="utf-8",
    )
    return w


def _ws(tmp_path):
    ws = tmp_path / "ws"
    (ws / "generated").mkdir(parents=True)
    return ws


def test_worker_runner_passes_prompt_as_single_argv_without_shell(tmp_path):
    worker = _record_arg_worker(tmp_path)
    out = tmp_path / "seen.txt"
    ws = _ws(tmp_path)
    cfg = {"executable": sys.executable, "args": [str(worker), str(out), "{prompt}"]}
    runner = orch.make_worker_runner(cfg, ws, tmp_path)
    # Contains shell metacharacters and newlines: a shell would mangle these.
    tricky = "line1\n\"double\" and 'single' & $HOME | rm -rf / ; `whoami`\nline3"
    code, _out = runner(tricky)
    assert code == 0
    assert out.read_text(encoding="utf-8") == tricky  # survived verbatim -> shell=False


def test_worker_runner_rejects_unknown_placeholder(tmp_path):
    ws = _ws(tmp_path)
    with pytest.raises(ValueError):
        orch.make_worker_runner({"executable": "echo", "args": ["{bogus_placeholder}"]}, ws, tmp_path)


def test_worker_runner_prompt_file_is_written_then_cleaned(tmp_path):
    worker = _record_file_worker(tmp_path)
    out = tmp_path / "seen.txt"
    ws = _ws(tmp_path)
    cfg = {"executable": sys.executable, "args": [str(worker), str(out), "{prompt_file}"]}
    runner = orch.make_worker_runner(cfg, ws, tmp_path)
    code, _out = runner("hello from a prompt file\nsecond line")
    assert code == 0
    assert out.read_text(encoding="utf-8") == "hello from a prompt file\nsecond line"
    # prompt file is cleaned up after the worker returns
    assert list((ws / "generated" / "prompts").glob("*")) == []


def test_worker_runner_substitutes_context_placeholders(tmp_path):
    worker = _record_arg_worker(tmp_path)
    out = tmp_path / "seen.txt"
    ws = _ws(tmp_path)
    cfg = {"executable": sys.executable, "args": [str(worker), str(out), "{task_id}"]}
    runner = orch.make_worker_runner(cfg, ws, tmp_path)
    code, _out = runner("ignored")
    assert code == 0
    assert out.read_text(encoding="utf-8") == ws.name  # {task_id} -> workspace name
