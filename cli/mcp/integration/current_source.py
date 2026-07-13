"""Current-source adapter — mechanical source verification (plan §13).

Current source is the authority for exact code facts. Unlike MCP providers,
this verification is fully mechanical: Maika hashes the file itself, so a
verification entry cannot be fabricated without the file actually matching.
Gates re-verify the hash at validation time.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

PROVIDER_ID = "current-source"


def verify_source(repo_root: Path, file: str, symbol: str | None = None) -> dict:
    path = Path(file)
    if not path.is_absolute():
        path = Path(repo_root) / file
    if not path.is_file():
        raise FileNotFoundError(f"source file not found: {file}")
    raw = path.read_bytes()
    if symbol and symbol not in raw.decode("utf-8", errors="replace"):
        raise ValueError(f"symbol {symbol!r} not found in {file}")
    entry = {
        "provider_id": PROVIDER_ID,
        "file": file,
        "sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
    }
    if symbol:
        entry["symbol"] = symbol
    return entry
