"""Capability probes for gate-check (impure — shells out to knowledge-tool CLIs).

Kept OUT of gates.py so the validators stay deterministic/hermetic. The caller
(cli.py) runs the probe and passes the result into the pure validator, mirroring
the existing --index pattern. Fail-open: most probes return an empty list on error
so a missing/broken probe never blocks (the validator treats empty as "nothing to
use → grep OK"). EXCEPTION: `changed_java_files` fails CLOSED (returns None on git
error) so the code-hygiene gate degrades loudly instead of silently passing.
"""
import json
import os
import subprocess


def _parse_list_projects(stdout: str):
    """Extract [{"name","root_path"}] from `codebase-memory-mcp cli list_projects`
    output. cbm prints a log line before the JSON, so scan lines from the end for
    the first that parses as an object."""
    for line in reversed(stdout.splitlines()):
        s = line.strip()
        if not s.startswith("{"):
            continue
        try:
            data = json.loads(s)
        except json.JSONDecodeError:
            continue
        return [
            {"name": p.get("name", ""), "root_path": p.get("root_path", "")}
            for p in data.get("projects", [])
            if p.get("root_path")
        ]
    return []


def cbm_indexed_projects(timeout: int = 8):
    """Projects indexed in codebase-memory-mcp. [] on any failure (fail-open)."""
    try:
        proc = subprocess.run(
            ["codebase-memory-mcp", "cli", "list_projects", "{}"],
            capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return _parse_list_projects(proc.stdout)


def ua_indexed_projects(candidate_roots):
    """Roots that have a UA knowledge-graph.json (UA can serve them)."""
    out = []
    for root in candidate_roots:
        if root and os.path.isfile(
            os.path.join(root, ".understand-anything", "knowledge-graph.json")
        ):
            out.append({"name": os.path.basename(root.rstrip("/")), "root_path": root})
    return out


def indexed_projects(repo_root: str | None = None, timeout: int = 8):
    """Union of projects any knowledge tool can serve (cbm ∪ UA-graph-present)."""
    projs = cbm_indexed_projects(timeout=timeout)
    roots = {p["root_path"] for p in projs}
    if repo_root:
        roots.add(repo_root)
    known = {p["root_path"] for p in projs}
    ua = [p for p in ua_indexed_projects(roots) if p["root_path"] not in known]
    return projs + ua


def _parse_snippet(stdout: str):
    """Last JSON object line from `get_code_snippet` output, or None."""
    for line in reversed(stdout.splitlines()):
        s = line.strip()
        if not s.startswith("{"):
            continue
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            continue
    return None


def verify_nodes(node_ids, timeout: int = 8):
    """Verify each node_id (a cbm qualified_name) exists in cbm's graph.

    Returns (verified, ok). verified = {node_id: file_path(abs)} for nodes that
    exist. ok=False if the cbm binary is absent / a probe raises (caller then
    fail-opens only with an embedded real cbm error). The project for each node
    is its qualified_name prefix (path->'-' names contain no dots)."""
    verified = {}
    for nid in node_ids:
        project = nid.split(".", 1)[0]
        try:
            proc = subprocess.run(
                ["codebase-memory-mcp", "cli", "get_code_snippet",
                 json.dumps({"project": project, "qualified_name": nid})],
                capture_output=True, text=True, timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError):
            return {}, False
        d = _parse_snippet(proc.stdout)
        if d and d.get("qualified_name") == nid and d.get("file_path"):
            verified[nid] = d["file_path"]
    return verified, True


def changed_java_files(repo_root, timeout: int = 8):
    """Changed .java files in the git repo containing repo_root (vs HEAD +
    untracked), absolute paths. repo_root được chuẩn hoá về git top-level qua
    rev-parse nên diff (top-relative) và ls-files (cwd-relative) join nhất quán;
    file đã xóa bị lọc (không thể chứa import thừa).
    Returns None when git cannot answer. DELIBERATELY not fail-open (khác các
    probe trên): code-hygiene gate phải degrade LOUDLY — validator FAILs on None."""
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             cwd=repo_root, capture_output=True, text=True,
                             timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if top.returncode != 0:
        return None
    root = top.stdout.strip()
    collected = []
    for cmd in (["git", "diff", "--name-only", "HEAD"],
                ["git", "ls-files", "--others", "--exclude-standard"]):
        try:
            proc = subprocess.run(cmd, cwd=root, capture_output=True,
                                  text=True, timeout=timeout)
        except (OSError, subprocess.SubprocessError):
            return None
        if proc.returncode != 0:
            return None
        collected += [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    paths = {os.path.join(root, f) for f in collected if f.endswith(".java")}
    return sorted(p for p in paths if os.path.isfile(p))
