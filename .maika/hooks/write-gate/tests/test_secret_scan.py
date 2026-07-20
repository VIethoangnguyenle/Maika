"""Tests for the inlined secret scanner in write_gate.py.

The scanner is side-effect-free: given text it returns matches whose
masked_preview NEVER contains the raw secret.
"""
import importlib.util
from pathlib import Path


MOD = Path(__file__).resolve().parents[1] / "write_gate.py"
spec = importlib.util.spec_from_file_location("write_gate", MOD)
wg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wg)


AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
JWT = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
       "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
       "dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U")
GITHUB = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"


def _rule_ids(matches):
    return {m.rule_id for m in matches}


def test_detects_aws_access_key():
    matches = wg._secret_scan(f"aws_key = {AWS_KEY}\n")
    assert "aws-access-key" in _rule_ids(matches)
    hit = next(m for m in matches if m.rule_id == "aws-access-key")
    assert AWS_KEY not in hit.masked_preview
    assert hit.masked_preview.startswith("AKIA")


def test_detects_pem_private_key():
    matches = wg._secret_scan("-----BEGIN RSA PRIVATE KEY-----\nMIIB...\n")
    assert "private-key" in _rule_ids(matches)


def test_detects_jwt():
    matches = wg._secret_scan(f"token: {JWT}\n")
    assert "jwt" in _rule_ids(matches)
    hit = next(m for m in matches if m.rule_id == "jwt")
    assert JWT not in hit.masked_preview


def test_detects_github_token():
    matches = wg._secret_scan(f"gh = {GITHUB}\n")
    assert "github-token" in _rule_ids(matches)


def test_generic_assignment_detects_quoted_secret():
    raw = "s3cr3t_value_1234567890"
    matches = wg._secret_scan(f'api_key = "{raw}"\n')
    assert "generic-assignment" in _rule_ids(matches)
    hit = next(m for m in matches if m.rule_id == "generic-assignment")
    assert raw not in hit.masked_preview


def test_clean_content_has_no_matches():
    body = "def add(a, b):\n    return a + b  # nothing secret here\n"
    assert wg._secret_scan(body) == []


def test_akia_word_in_prose_is_not_matched():
    assert wg._secret_scan("AKIA is just a prefix we talk about.\n") == []


def test_reports_line_number():
    body = f"line one\nline two\naws = {AWS_KEY}\n"
    hit = next(m for m in wg._secret_scan(body) if m.rule_id == "aws-access-key")
    assert hit.line == 3


def test_mask_never_contains_raw_middle():
    masked = wg._mask_secret(AWS_KEY)
    assert masked.startswith("AKIA")
    assert masked.endswith("LE")
    assert "IOSFODNN7" not in masked
    assert "****" in masked


def test_mask_short_value_fully_hidden():
    assert wg._mask_secret("abcd") == "****"
