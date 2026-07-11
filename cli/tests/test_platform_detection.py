"""Tests for host platform detection.

Detection separates advertised (adapter declares) from detected (binary present)
capabilities and must NEVER claim `verified` — verification requires a smoke path.
"""

from cli.platforms import get_platform
from cli.platforms import detection


def test_binary_missing_keeps_caps_advertised(monkeypatch):
    monkeypatch.setattr(detection, "detect_binary", lambda name: {"found": False, "path": None, "name": name})
    result = detection.detect_platform(get_platform("claude-code"))
    assert result["binary"]["found"] is False
    # Advertised capabilities stay 'advertised' — a missing binary is not 'detected'.
    advertised = {cap for cap, on in get_platform("claude-code").capabilities.items() if on}
    assert advertised, "expected claude-code to advertise something"
    assert all(result["capabilities"][cap] == "advertised" for cap in advertised)
    assert "verified" not in result["capabilities"].values()


def test_binary_present_marks_caps_detected_not_verified(monkeypatch):
    monkeypatch.setattr(detection, "detect_binary",
                        lambda name: {"found": True, "path": f"/usr/bin/{name}", "name": name})
    monkeypatch.setattr(detection, "probe_version",
                        lambda argv, timeout=5: {"ok": True, "raw": "1.2.3", "returncode": 0})
    result = detection.detect_platform(get_platform("claude-code"))
    assert result["binary"]["found"] is True
    advertised = {cap for cap, on in get_platform("claude-code").capabilities.items() if on}
    assert all(result["capabilities"][cap] == "detected" for cap in advertised)
    # Detection alone never promotes to verified.
    assert "verified" not in result["capabilities"].values()


def test_unadvertised_capability_is_unavailable(monkeypatch):
    monkeypatch.setattr(detection, "detect_binary",
                        lambda name: {"found": True, "path": f"/usr/bin/{name}", "name": name})
    monkeypatch.setattr(detection, "probe_version",
                        lambda argv, timeout=5: {"ok": True, "raw": "1.0", "returncode": 0})
    platform = get_platform("claude-code")
    result = detection.detect_platform(platform)
    unadvertised = {cap for cap, on in platform.capabilities.items() if not on}
    assert all(result["capabilities"][cap] == "unavailable" for cap in unadvertised)


def test_probe_version_missing_binary_is_not_ok():
    # A non-existent binary must not raise; it reports ok=False.
    result = detection.probe_version(["maika-nonexistent-binary-xyz", "--version"], timeout=2)
    assert result["ok"] is False


def test_generic_platform_has_no_worker_binary(monkeypatch):
    result = detection.detect_platform(get_platform("generic"))
    assert result["binary"]["found"] is False  # generic has no CLI binary
