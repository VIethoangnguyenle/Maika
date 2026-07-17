"""MCP config loading and redaction helpers."""

from __future__ import annotations

import json
from ast import literal_eval
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # Python 3.9-3.10
    tomllib = None

from cli.mcp.adapters import McpConfigCandidate


_SECRET_KEYS = ("authorization", "token", "secret", "password", "api_key", "apikey", "key")
_TOML_DECODE_ERROR = getattr(tomllib, "TOMLDecodeError", ValueError)


@dataclass(frozen=True)
class LoadedMcpConfig:
    path: Path
    format: str
    exists: bool
    valid: bool
    servers: dict[str, dict[str, Any]]
    error: str = ""


def _extract_servers(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    for key in ("mcpServers", "mcp_servers"):
        value = data.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _load_raw(candidate: McpConfigCandidate) -> tuple[bool, str]:
    if not candidate.path.exists():
        return False, ""
    return True, candidate.path.read_text(encoding="utf-8")


def _parse_toml_value(raw_value: str) -> Any:
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        if raw_value.startswith("'") and raw_value.endswith("'"):
            return raw_value[1:-1]
        try:
            return literal_eval(raw_value)
        except (ValueError, SyntaxError) as exc:
            raise ValueError(f"unsupported TOML value: {raw_value}") from exc


def _parse_toml_fallback(raw: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_table: dict[str, Any] | None = None

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
            parts = [part.strip() for part in section.split(".") if part.strip()]
            if not parts:
                raise ValueError("empty TOML section")
            current_table = data
            for part in parts:
                next_value = current_table.get(part)
                if next_value is None:
                    next_value = {}
                    current_table[part] = next_value
                if not isinstance(next_value, dict):
                    raise ValueError(f"TOML section {section!r} conflicts with a value")
                current_table = next_value
            continue
        if current_table is None:
            continue
        if "=" not in stripped:
            raise ValueError(f"invalid TOML line: {line}")
        key, raw_value = stripped.split("=", 1)
        current_table[key.strip()] = _parse_toml_value(raw_value.strip())

    return data


def _parse_toml(raw: str) -> dict[str, Any]:
    if tomllib is not None:
        return tomllib.loads(raw)
    return _parse_toml_fallback(raw)


def load_mcp_config(candidate: McpConfigCandidate) -> LoadedMcpConfig:
    exists, raw = _load_raw(candidate)
    if not exists:
        return LoadedMcpConfig(candidate.path, candidate.format, False, False, {}, "missing")
    if not raw.strip():
        return LoadedMcpConfig(candidate.path, candidate.format, True, False, {}, "empty config")

    try:
        if candidate.format == "json":
            data = json.loads(raw)
        elif candidate.format == "toml":
            data = _parse_toml(raw)
        else:
            return LoadedMcpConfig(
                candidate.path,
                candidate.format,
                True,
                False,
                {},
                "unsupported format",
            )
    except (json.JSONDecodeError, _TOML_DECODE_ERROR, ValueError, SyntaxError):
        return LoadedMcpConfig(
            candidate.path,
            candidate.format,
            True,
            False,
            {},
            f"invalid {candidate.format}",
        )

    if not isinstance(data, dict):
        return LoadedMcpConfig(candidate.path, candidate.format, True, False, {}, "config root is not an object")

    servers = _extract_servers(data)
    if not servers:
        return LoadedMcpConfig(candidate.path, candidate.format, True, False, {}, "missing mcpServers")

    return LoadedMcpConfig(candidate.path, candidate.format, True, True, servers)


def server_names(config: LoadedMcpConfig) -> list[str]:
    return list(config.servers)


def selected_server_matches(config: LoadedMcpConfig, selected: list[str]) -> tuple[list[str], list[str]]:
    names = set(server_names(config))
    present = [name for name in selected if name in names]
    missing = [name for name in selected if name not in names]
    return present, missing


def _looks_sensitive(key: Any) -> bool:
    key_text = str(key).lower()
    return any(secret in key_text for secret in _SECRET_KEYS)


def redact_mapping(value: Any) -> Any:
    return _redact_mapping(value)


def _redact_mapping(value: Any, *, redact_values: bool = False) -> Any:
    if isinstance(value, dict):
        redacted: dict[Any, Any] = {}
        for key, item in value.items():
            child_redacts_values = (
                redact_values or str(key).lower() in {"env", "headers"}
            )
            if redact_values:
                redacted[key] = _redact_mapping(item, redact_values=True)
            elif _looks_sensitive(key):
                redacted[key] = "<redacted>"
            else:
                redacted[key] = _redact_mapping(item, redact_values=child_redacts_values)
        return redacted
    if isinstance(value, list):
        return [_redact_mapping(item, redact_values=redact_values) for item in value]
    return "<redacted>" if redact_values else value
