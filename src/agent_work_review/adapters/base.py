from __future__ import annotations

from typing import Protocol


class EvidenceAdapter(Protocol):
    """Contract for adapters that normalize an Agent's history into evidence records."""

    name: str

    def collect(self) -> list[dict]: ...
