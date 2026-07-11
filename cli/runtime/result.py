"""Shared lifecycle operation result contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class OperationResult:
    status: str
    mutation: bool
    project_data_mutation: bool = False
    diagnostic_mutation: bool = False
    exit_code: int = 0
    transaction_id: Optional[str] = None
    message: str = ""

    def __post_init__(self) -> None:
        if self.status not in {"no-op", "committed", "blocked", "partial-safe"}:
            raise ValueError(f"unknown operation status: {self.status}")
        if self.status == "blocked" and self.mutation:
            raise ValueError("blocked operation cannot report mutation")
        if self.status in {"no-op", "committed"} and self.exit_code != 0:
            raise ValueError(f"{self.status} operation must exit 0")
        if self.status in {"blocked", "partial-safe"} and self.exit_code == 0:
            raise ValueError(f"{self.status} operation must exit non-zero")
        if (self.project_data_mutation or self.diagnostic_mutation) and not self.mutation:
            raise ValueError("mutation detail requires mutation=true")

    def to_dict(self) -> dict:
        return asdict(self)
