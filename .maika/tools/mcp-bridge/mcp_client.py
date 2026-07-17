#!/usr/bin/env python3
"""Controlled MCP bridge for Maika diagnostics and fallback use."""

import argparse
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


PROTOCOL_VERSION = "2024-11-05"
REQUEST_TIMEOUT_SECONDS = 15
READER_JOIN_TIMEOUT_SECONDS = 1


def parse_sse(response_text: str):
    for line in response_text.splitlines():
        if line.startswith("data: "):
            try:
                return json.loads(line[6:])
            except json.JSONDecodeError:
                return None
    return None


def parse_sse_events(response_text: str):
    events = []
    event_name = "message"
    data_lines = []
    for line in response_text.splitlines():
        if line.startswith("event: "):
            event_name = line[7:].strip() or "message"
            continue
        if line.startswith("data: "):
            data_lines.append(line[6:])
            continue
        if not line and data_lines:
            events.append((event_name, "\n".join(data_lines)))
            event_name = "message"
            data_lines = []
    if data_lines:
        events.append((event_name, "\n".join(data_lines)))
    return events


def emit(ok: bool, server: str, operation: str, result=None, error: str = "") -> int:
    print(
        json.dumps(
            {
                "ok": ok,
                "server": server,
                "operation": operation,
                "result": result,
                "error": error,
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


def load_config(config_path: Path, server: str):
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    servers = data.get("mcpServers") or data.get("mcp_servers") or {}
    selected = servers.get(server)
    return selected if isinstance(selected, dict) else None


def request_payload(method: str, params: dict, req_id: int) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}) + "\n"


def notification_payload(method: str, params: dict) -> str:
    return json.dumps({"jsonrpc": "2.0", "method": method, "params": params}) + "\n"


def initialize_params() -> dict:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": "maika-mcp-bridge", "version": "1.0.0"},
    }


def validate_response(method: str, response):
    if response is None:
        return f"{method} failed: no valid JSON-RPC response"
    if not isinstance(response, dict) or response.get("jsonrpc") != "2.0":
        return f"{method} failed: malformed JSON-RPC response"
    if "error" in response:
        message = response["error"]
        if isinstance(message, dict):
            message = message.get("message") or "server returned an error"
        return f"{method} failed: {message}"
    if "result" not in response:
        return f"{method} failed: malformed JSON-RPC response"
    return ""


def discover_sse_message_endpoint(sse_url: str, headers: dict) -> str:
    req = urllib.request.Request(
        sse_url,
        headers={**headers, "Accept": "text/event-stream"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
    for event_name, data in parse_sse_events(body):
        if event_name == "endpoint":
            return urllib.parse.urljoin(sse_url, data.strip())
    raise ValueError("legacy SSE discovery failed: endpoint event missing")


def normalize_mcp_endpoint(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    if parsed.path.endswith("/mcp"):
        return url
    return ""


def resolve_http_endpoint(config: dict, headers: dict) -> str:
    if config.get("serverUrl"):
        url = config["serverUrl"]
        if not url.endswith("/mcp"):
            url = url.rstrip("/") + "/mcp"
        return url
    direct_url = normalize_mcp_endpoint(config.get("url", ""))
    if direct_url:
        return direct_url
    if config.get("sseUrl"):
        return discover_sse_message_endpoint(config["sseUrl"], headers)
    if config.get("url"):
        return discover_sse_message_endpoint(config["url"], headers)
    raise ValueError("http server has no serverUrl")


def _close_pipe(pipe) -> None:
    if pipe is None or not hasattr(pipe, "close"):
        return
    try:
        pipe.close()
    except (OSError, ValueError):
        pass


def _has_process_group(proc) -> bool:
    return os.name == "posix" and isinstance(getattr(proc, "pid", None), int)


def _signal_stdio_process(proc, *, force: bool) -> None:
    if _has_process_group(proc):
        try:
            os.killpg(proc.pid, signal.SIGKILL if force else signal.SIGTERM)
        except ProcessLookupError:
            pass
        return
    try:
        (proc.kill if force else proc.terminate)()
    except ProcessLookupError:
        pass


def _shutdown_stdio_process(proc, reader_threads: list[threading.Thread]) -> None:
    """Close bridge pipes, reap the child, and boundedly join response readers."""
    _close_pipe(proc.stdin)
    reaped = False
    _signal_stdio_process(proc, force=False)
    try:
        proc.wait(timeout=1)
        reaped = True
    except subprocess.TimeoutExpired:
        _signal_stdio_process(proc, force=True)
        try:
            proc.wait(timeout=1)
            reaped = True
        except subprocess.TimeoutExpired:
            pass

    # A direct child can exit while one of its descendants still owns stdout.
    # Once the direct child is reaped, force-stop any surviving POSIX group
    # members so the reader can observe EOF without a cross-thread close.
    if reaped and _has_process_group(proc):
        _signal_stdio_process(proc, force=True)
    for reader in reader_threads:
        reader.join(timeout=READER_JOIN_TIMEOUT_SECONDS)
    # BufferedReader.close() can wait on a lock held by readline(). Never call
    # it until every reader has exited; on non-POSIX a daemon reader may remain
    # briefly if a descendant inherited stdout, but cleanup itself stays bound.
    if all(not reader.is_alive() for reader in reader_threads):
        _close_pipe(proc.stdout)


def with_stdio_session(config: dict, callback):
    """Run bounded callback operations over one initialized stdio process."""
    command = config.get("command")
    if not command:
        return None, "stdio server has no command"
    args = config.get("args") or []
    env = os.environ.copy()
    env.update(config.get("env") or {})
    proc = subprocess.Popen(
        [command, *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env=env,
        start_new_session=os.name == "posix",
    )
    reader_threads = []
    next_request_id = 2

    def send(method: str, params: dict, req_id: int):
        deadline = time.monotonic() + REQUEST_TIMEOUT_SECONDS
        proc.stdin.write(request_payload(method, params, req_id))
        proc.stdin.flush()
        responses = queue.Queue(maxsize=1)

        def read_response():
            while True:
                try:
                    line = proc.stdout.readline()
                except (OSError, ValueError):
                    responses.put(None)
                    return
                if not line:
                    responses.put(None)
                    return
                if "jsonrpc" not in line:
                    continue
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(message, dict):
                    continue
                if message.get("jsonrpc") != "2.0":
                    continue
                if message.get("id") != req_id:
                    continue
                responses.put(message)
                return

        reader = threading.Thread(target=read_response, daemon=True)
        reader_threads.append(reader)
        reader.start()
        try:
            remaining = max(0.0, deadline - time.monotonic())
            return responses.get(timeout=remaining)
        except queue.Empty as exc:
            raise TimeoutError(f"{method} failed: timed out") from exc

    def notify(method: str, params: dict):
        proc.stdin.write(notification_payload(method, params))
        proc.stdin.flush()

    try:
        init = send("initialize", initialize_params(), 1)
        error = validate_response("initialize", init)
        if error:
            return None, error
        notify("notifications/initialized", {})

        def call(operation: str, tool_name: str | None, arguments: dict):
            nonlocal next_request_id
            if operation == "tools-list":
                method, params = "tools/list", {}
            else:
                method = "tools/call"
                params = {"name": tool_name, "arguments": arguments}
            request_id = next_request_id
            next_request_id += 1
            result = send(method, params, request_id)
            call_error = validate_response(method, result)
            return (result if not call_error else None), call_error

        return callback(call), ""
    except TimeoutError as exc:
        return None, str(exc)
    finally:
        _shutdown_stdio_process(proc, reader_threads)


def call_stdio(config: dict, operation: str, tool_name: str | None, arguments: dict):
    outcome, session_error = with_stdio_session(
        config, lambda call: call(operation, tool_name, arguments),
    )
    if session_error:
        return None, session_error
    return outcome


def call_http(config: dict, operation: str, tool_name: str | None, arguments: dict):
    headers = dict(config.get("headers") or {})
    headers.update({"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})

    try:
        url = resolve_http_endpoint(config, headers)
    except (urllib.error.URLError, ValueError) as exc:
        return None, str(exc)

    def post(method: str, params: dict, session_id: str | None = None):
        req_headers = dict(headers)
        if session_id:
            req_headers["mcp-session-id"] = session_id
        req = urllib.request.Request(
            url,
            data=request_payload(method, params, 1).encode("utf-8"),
            headers=req_headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            parsed = parse_sse(body) if body else None
            if parsed is None and body:
                parsed = json.loads(body)
            return parsed, resp.headers.get("mcp-session-id")

    def post_notification(method: str, params: dict, session_id: str | None = None):
        req_headers = dict(headers)
        if session_id:
            req_headers["mcp-session-id"] = session_id
        req = urllib.request.Request(
            url,
            data=notification_payload(method, params).encode("utf-8"),
            headers=req_headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15):
            return None

    try:
        init, session = post("initialize", initialize_params())
        error = validate_response("initialize", init)
        if error:
            return None, error
        post_notification("notifications/initialized", {}, session)
        if operation == "tools-list":
            result, _ = post("tools/list", {}, session)
            error = validate_response("tools/list", result)
        else:
            result, _ = post("tools/call", {"name": tool_name, "arguments": arguments}, session)
            error = validate_response("tools/call", result)
        return (result if not error else None), error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        return None, str(exc)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--server", required=True)
    sub = parser.add_subparsers(dest="operation", required=True)
    sub.add_parser("tools-list")
    call = sub.add_parser("call")
    call.add_argument("tool")
    call.add_argument("--arguments", default="{}")
    args = parser.parse_args(argv)

    config = load_config(Path(args.config), args.server)
    if config is None:
        return emit(False, args.server, args.operation, error="server not found or config invalid")
    try:
        arguments = json.loads(getattr(args, "arguments", "{}"))
    except json.JSONDecodeError as exc:
        return emit(False, args.server, args.operation, error=f"invalid arguments JSON: {exc}")

    if "command" in config:
        result, error = call_stdio(config, args.operation, getattr(args, "tool", None), arguments)
    else:
        result, error = call_http(config, args.operation, getattr(args, "tool", None), arguments)
    return emit(error == "", args.server, args.operation, result=result, error=error)


if __name__ == "__main__":
    sys.exit(main())
