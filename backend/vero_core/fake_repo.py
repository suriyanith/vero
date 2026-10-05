"""In-memory CodeRepository for tests and the CLI's fake mode.

Search is naive word overlap — deliberately simple. It stands in for the
Postgres implementation in unit tests; ranking quality is tested against the
real repository in the Django test suite.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from vero_core.schemas import Candidate


def _tokens(text: str) -> set[str]:
    return {token for token in text.lower().replace(",", " ").split() if token}


@dataclass
class FakeCodeRepository:
    candidates: list[Candidate]

    @classmethod
    def from_json(cls, path: Path) -> "FakeCodeRepository":
        """Load from a JSON list of Candidate dicts (see data/fixtures/)."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(candidates=[Candidate.model_validate(item) for item in raw])

    def search(self, query: str, limit: int = 10, billable_only: bool = True) -> list[Candidate]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []
        scored: list[tuple[float, Candidate]] = []
        for candidate in self.candidates:
            if billable_only and not candidate.is_billable:
                continue
            description_tokens = _tokens(candidate.description)
            overlap = len(query_tokens & description_tokens)
            if overlap == 0:
                continue
            # Favor descriptions that cover the query and are not much longer.
            score = overlap / len(query_tokens) - 0.01 * len(description_tokens)
            scored.append((score, candidate))
        scored.sort(key=lambda pair: (-pair[0], pair[1].code))
        return [
            candidate.model_copy(update={"rank": position})
            for position, (_, candidate) in enumerate(scored[:limit], start=1)
        ]

    def get(self, display_code: str) -> Candidate | None:
        wanted = display_code.replace(".", "").upper()
        for candidate in self.candidates:
            if candidate.code == wanted:
                return candidate
        return None

    def billable_in_category(self, category: str) -> list[Candidate]:
        return [c for c in self.candidates if c.category == category and c.is_billable]
