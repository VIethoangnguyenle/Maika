import importlib.util
import json
import time
from pathlib import Path


BRIDGE = Path(__file__).resolve().parents[2] / ".maika" / "tools" / "mcp-bridge" / "mcp_client.py"


def load_bridge():
    spec = importlib.util.spec_from_file_location("mcp_client", BRIDGE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_sse_returns_first_json_data_event():
    bridge = load_bridge()
    text = "event: message\ndata: {\"jsonrpc\":\"2.0\",\"result\":{\"ok\":true}}\n\n"
    assert bridge.parse_sse(text)["result"]["ok"] is True


def test_load_config_requires_explicit_path(tmp_path):
    bridge = load_bridge()
    path = tmp_path / "mcp_config.json"
    path.write_text(json.dumps({"mcpServers": {"demo": {"command": "python"}}}), encoding="utf-8")

    config = bridge.load_config(path, "demo")

    assert config["command"] == "python"


def test_load_config_rejects_missing_server_without_printing_config(tmp_path):
    bridge = load_bridge()
    path = tmp_path / "mcp_config.json"
    path.write_text(json.dumps({"mcpServers": {"demo": {"headers": {"Authorization": "secret"}}}}), encoding="utf-8")

    result = bridge.load_config(path, "other")

    assert result is None


def test_call_stdio_sends_initialized_notification_before_tools_list(monkeypatch):
    bridge = load_bridge()
    writes = []
    responses = iter(
        [
            '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05"}}\n',
            '{"jsonrpc":"2.0","id":2,"result":{"tools":[]}}\n',
        ]
    )

    class FakeStdin:
        def write(self, text):
            writes.append(json.loads(text))

        def flush(self):
            return None

    class FakeStdout:
        def readline(self):
            return next(responses, "")

    class FakeProcess:
        def __init__(self):
            self.stdin = FakeStdin()
            self.stdout = FakeStdout()

        def terminate(self):
            return None

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(bridge.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())

    result, error = bridge.call_stdio({"command": "python"}, "tools-list", None, {})

    assert error == ""
    assert result["result"]["tools"] == []
    assert [entry["method"] for entry in writes] == [
        "initialize",
        "notifications/initialized",
        "tools/list",
    ]
    assert "id" not in writes[1]
    assert writes[1]["params"] == {}


def test_call_stdio_returns_error_when_tools_list_response_missing(monkeypatch):
    bridge = load_bridge()
    responses = iter(['{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05"}}\n'])

    class FakeStdin:
        def write(self, text):
            return None

        def flush(self):
            return None

    class FakeStdout:
        def readline(self):
            return next(responses, "")

    class FakeProcess:
        def __init__(self):
            self.stdin = FakeStdin()
            self.stdout = FakeStdout()

        def terminate(self):
            return None

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(bridge.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())

    result, error = bridge.call_stdio({"command": "python"}, "tools-list", None, {})

    assert result is None
    assert error == "tools/list failed: no valid JSON-RPC response"


def test_call_stdio_times_out_and_terminates_unresponsive_server(monkeypatch):
    bridge = load_bridge()
    terminated = []

    class FakeStdin:
        def write(self, text):
            return None

        def flush(self):
            return None

    class FakeStdout:
        def readline(self):
            time.sleep(1)
            return ""

    class FakeProcess:
        def __init__(self):
            self.stdin = FakeStdin()
            self.stdout = FakeStdout()

        def terminate(self):
            terminated.append(True)

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(bridge, "REQUEST_TIMEOUT_SECONDS", 0.01, raising=False)
    monkeypatch.setattr(bridge.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())

    result, error = bridge.call_stdio({"command": "python"}, "tools-list", None, {})

    assert result is None
    assert error == "initialize failed: timed out"
    assert terminated == [True]


def test_runtime_probe_reuses_loaded_bridge_for_tools_list(tmp_path):
    from cli.mcp.runtime_probe import probe_tools_list

    bridge = tmp_path / "fake_bridge.py"
    bridge.write_text(
        "def call_stdio(server, operation, tool_name, arguments):\n"
        "    assert operation == 'tools-list'\n"
        "    return ({'result': {'tools': [{'name': 'find_symbol'}]}}, '')\n",
        encoding="utf-8",
    )

    result, error = probe_tools_list({"command": "serena"}, bridge)

    assert error == ""
    assert result == {"tools": [{"name": "find_symbol"}]}


def test_discover_sse_message_endpoint_reads_endpoint_event(monkeypatch):
    bridge = load_bridge()

    class FakeResponse:
        def __init__(self, body: str):
            self._body = body.encode("utf-8")

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout=15):
        assert request.get_method() == "GET"
        assert request.full_url == "http://example.test/sse"
        return FakeResponse("event: endpoint\ndata: /messages?session_id=abc\n\n")

    monkeypatch.setattr(bridge.urllib.request, "urlopen", fake_urlopen)

    message_url = bridge.discover_sse_message_endpoint("http://example.test/sse", {})

    assert message_url == "http://example.test/messages?session_id=abc"


def test_call_http_sends_initialized_notification_before_tools_list(monkeypatch):
    bridge = load_bridge()
    requests = []

    class FakeResponse:
        def __init__(self, body, session_id=None):
            self._body = body.encode("utf-8")
            self.headers = {}
            if session_id is not None:
                self.headers["mcp-session-id"] = session_id

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(bridge, "resolve_http_endpoint", lambda config, headers: "https://host.test/mcp")

    def fake_urlopen(request, timeout=15):
        payload = json.loads(request.data.decode("utf-8"))
        request_headers = {key.lower(): value for key, value in request.headers.items()}
        requests.append(
            {
                "method": request.get_method(),
                "url": request.full_url,
                "payload": payload,
                "session": request_headers.get("mcp-session-id"),
            }
        )
        if payload["method"] == "initialize":
            return FakeResponse(
                '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05"}}',
                session_id="session-123",
            )
        if payload["method"] == "notifications/initialized":
            return FakeResponse("", session_id="session-123")
        if payload["method"] == "tools/list":
            return FakeResponse('{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}')
        raise AssertionError(f"unexpected method {payload['method']}")

    monkeypatch.setattr(bridge.urllib.request, "urlopen", fake_urlopen)

    result, error = bridge.call_http({"serverUrl": "https://host.test/mcp"}, "tools-list", None, {})

    assert error == ""
    assert result["result"]["tools"] == []
    assert [entry["payload"]["method"] for entry in requests] == [
        "initialize",
        "notifications/initialized",
        "tools/list",
    ]
    assert requests[1]["payload"]["params"] == {}
    assert requests[1]["session"] == "session-123"
    assert requests[2]["session"] == "session-123"


def test_resolve_http_endpoint_preserves_direct_post_url_and_explicit_sse_fallback(monkeypatch):
    bridge = load_bridge()
    discovered = []

    def fake_discover(url, headers):
        discovered.append(url)
        return "https://host.test/messages?session_id=legacy"

    monkeypatch.setattr(bridge, "discover_sse_message_endpoint", fake_discover)

    direct_url = bridge.resolve_http_endpoint({"url": "https://host.test/mcp"}, {})
    fallback_url = bridge.resolve_http_endpoint({"url": "https://host.test/sse"}, {})
    explicit_sse_url = bridge.resolve_http_endpoint({"sseUrl": "https://host.test/events"}, {})

    assert direct_url == "https://host.test/mcp"
    assert fallback_url == "https://host.test/messages?session_id=legacy"
    assert explicit_sse_url == "https://host.test/messages?session_id=legacy"
    assert discovered == ["https://host.test/sse", "https://host.test/events"]
