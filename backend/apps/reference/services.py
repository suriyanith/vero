"""Code lookup and search against the active reference data.

PostgresCodeRepository implements the `CodeRepository` protocol from
`vero_core.interfaces`; the same search powers the pipeline's candidate
retrieval and the UI's code-search box.
"""

from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramSimilarity
from django.db.models import F, Q, QuerySet

from apps.reference.models import CodeSetVersion, HccModel, Icd10Code, Icd10HccMap
from vero_core.schemas import Candidate

# Combined score: mostly full-text relevance, trigram similarity as a
# secondary signal and a fallback for typos/abbreviations. Tune on the dev set.
TEXT_RANK_WEIGHT = 0.7
TRIGRAM_WEIGHT = 0.3
TRIGRAM_FLOOR = 0.1  # below this, a trigram-only match is noise


def active_code_set() -> CodeSetVersion | None:
    return CodeSetVersion.objects.filter(is_active=True).first()


def active_hcc_model() -> HccModel | None:
    return HccModel.objects.filter(is_active=True).first()


class PostgresCodeRepository:
    """Search and lookups over one code set + HCC model (the active ones)."""

    def __init__(
        self,
        code_set: CodeSetVersion | None = None,
        hcc_model: HccModel | None = None,
    ) -> None:
        resolved = code_set or active_code_set()
        if resolved is None:
            raise ValueError("No active ICD-10-CM code set is loaded.")
        self.code_set = resolved
        self.hcc_model = hcc_model or active_hcc_model()

    def _codes(self) -> QuerySet[Icd10Code]:
        return Icd10Code.objects.filter(code_set=self.code_set)

    def hcc_lookup(self, codes: list[str]) -> dict[str, tuple[int, str]]:
        """Dotless code → (hcc number, label) under the active model."""
        if self.hcc_model is None:
            return {}
        mappings = Icd10HccMap.objects.filter(model=self.hcc_model, code__in=codes).select_related(
            "hcc"
        )
        return {m.code: (m.hcc.number, m.hcc.label) for m in mappings}

    def _to_candidates(self, codes: list[Icd10Code], ranked: bool) -> list[Candidate]:
        hccs = self.hcc_lookup([c.code for c in codes])
        candidates = []
        for position, code in enumerate(codes, start=1):
            hcc = hccs.get(code.code)
            candidates.append(
                Candidate(
                    code=code.code,
                    display_code=code.display_code,
                    description=code.long_desc,
                    is_billable=code.is_billable,
                    rank=position if ranked else 0,
                    category=code.category,
                    notes=code.notes,
                    hcc_number=hcc[0] if hcc else None,
                    hcc_label=hcc[1] if hcc else None,
                )
            )
        return candidates

    def search(self, query: str, limit: int = 10, billable_only: bool = True) -> list[Candidate]:
        query = query.strip()
        if not query:
            return []
        qs = self._codes()
        if billable_only:
            qs = qs.filter(is_billable=True)

        search_query = SearchQuery(query, search_type="websearch", config="english")
        qs = (
            qs.annotate(
                # normalization=32 maps rank into (0, 1): rank / (rank + 1)
                text_rank=SearchRank(F("search_vector"), search_query, normalization=32),
                similarity=TrigramSimilarity("long_desc", query),
            )
            .annotate(score=TEXT_RANK_WEIGHT * F("text_rank") + TRIGRAM_WEIGHT * F("similarity"))
            .filter(Q(search_vector=search_query) | Q(similarity__gt=TRIGRAM_FLOOR))
            .order_by("-score", "code")
        )
        return self._to_candidates(list(qs[:limit]), ranked=True)

    def get(self, display_code: str) -> Candidate | None:
        code = self._codes().filter(code=display_code.replace(".", "").upper()).first()
        if code is None:
            return None
        return self._to_candidates([code], ranked=False)[0]

    def billable_in_category(self, category: str) -> list[Candidate]:
        codes = list(self._codes().filter(category=category, is_billable=True).order_by("code"))
        return self._to_candidates(codes, ranked=False)
