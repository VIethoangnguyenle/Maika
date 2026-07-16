#!/usr/bin/env python3
"""Controlled MCP bridge for Maika diagnostics and fallback use."""

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


PROTOCOL_VERSION = "2024-11-05"
REQUEST_TIMEOUT_SECONDS = 15


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


def call_stdio(config: dict, operation: str, tool_name: str | None, arguments: dict):
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
    )

    def send(method: str, params: dict, req_id: int):
        proc.stdin.write(request_payload(method, params, req_id))
        proc.stdin.flush()
        responses = queue.Queue(maxsize=1)

        def read_response():
            while True:
                line = proc.stdout.readline()
                if not line:
                    responses.put(None)
                    return
                if "jsonrpc" not in line:
                    continue
                try:
                    responses.put(json.loads(line))
                    return
                except json.JSONDecodeError:
                    continue

        threading.Thread(target=read_response, daemon=True).start()
        try:
            return responses.get(timeout=REQUEST_TIMEOUT_SECONDS)
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
        if operation == "tools-list":
            result = send("tools/list", {}, 2)
            error = validate_response("tools/list", result)
            return (result if not error else None), error
        result = send("tools/call", {"name": tool_name, "arguments": arguments}, 2)
        error = validate_response("tools/call", result)
        return (result if not error else None), error
    except TimeoutError as exc:
        return None, str(exc)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proc.kill()


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
