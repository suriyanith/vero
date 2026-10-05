"""Step 3 — Retrieve candidate codes (Python, no AI)."""

from vero_core.interfaces import CodeRepository, PipelineConfig
from vero_core.schemas import Candidate, VerifiedCondition


def build_query(condition: VerifiedCondition) -> str:
    return " ".join([condition.label, *condition.specificity_details]).strip()


def retrieve_candidates(
    condition: VerifiedCondition, codes: CodeRepository, config: PipelineConfig
) -> list[Candidate]:
    """Top-k search results plus the billable siblings of the top categories.

    Category expansion lets the selector pick a more specific code in the
    same family than the one search surfaced; an expanded code inherits the
    rank of the result it was expanded from (the confidence rules use rank).
    """
    hits = codes.search(build_query(condition), limit=config.retrieval_top_k, billable_only=True)

    by_code: dict[str, Candidate] = {hit.code: hit for hit in hits}
    for hit in hits[: config.category_expansion_top]:
        for sibling in codes.billable_in_category(hit.category):
            if sibling.code not in by_code:
                by_code[sibling.code] = sibling.model_copy(update={"rank": hit.rank})

    ordered = sorted(by_code.values(), key=lambda c: (c.rank, c.code))
    return ordered[: config.max_candidates_per_condition]
