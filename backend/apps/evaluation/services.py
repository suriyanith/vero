"""Run the pipeline over a labeled split and score it."""

import subprocess
from dataclasses import dataclass

from apps.evaluation.metrics import (
    AuditCaseResult,
    CodingNoteResult,
    audit_metrics,
    coding_metrics,
    operational_metrics,
)
from apps.evaluation.models import AuditCase, EvalRun, GoldLabel, GoldNonCode
from apps.llm.factory import build_llm_client
from apps.notes.models import Note
from apps.reference.services import PostgresCodeRepository
from apps.runs.services import PIPELINE_VERSION
from vero_core.errors import PipelineError
from vero_core.interfaces import PipelineConfig, PipelineDeps
from vero_core.pipeline import audit_note, code_note
from vero_core.schemas import CodingResult


class EvalError(Exception):
    pass


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return ""


def check_reviewed(notes: list[Note], allow_unreviewed: bool) -> bool:
    """Returns provisional=True when running on unreviewed labels."""
    unreviewed = GoldLabel.objects.filter(note__in=notes, reviewed=False).exists() or (
        GoldNonCode.objects.filter(note__in=notes, reviewed=False).exists()
    )
    if unreviewed and not allow_unreviewed:
        raise EvalError(
            "The split contains unreviewed labels. Review them in the admin or pass "
            "--allow-unreviewed (results will be marked provisional)."
        )
    return unreviewed


@dataclass
class EvalContext:
    deps: PipelineDeps
    config: PipelineConfig
    repo: PostgresCodeRepository


def build_context() -> EvalContext:
    from django.conf import settings

    repo = PostgresCodeRepository()
    return EvalContext(
        deps=PipelineDeps(llm=build_llm_client(), codes=repo),
        config=PipelineConfig(
            model_name=settings.GEMINI_MODEL or "fake",
            retrieval_top_k=settings.VERO_RETRIEVAL_TOP_K,
        ),
        repo=repo,
    )


def _score_coding_note(
    note: Note, result: CodingResult | None, ctx: EvalContext
) -> CodingNoteResult:
    gold_codes = {g.display_code for g in note.gold_labels.all()}
    gold_hccs = {
        hcc
        for _, (hcc, _) in ctx.repo.hcc_lookup(
            [code.replace(".", "") for code in gold_codes]
        ).items()
    }
    non_codes = [(g.condition_label, g.reason) for g in note.gold_non_codes.all()]
    if result is None:
        return CodingNoteResult(
            note_title=note.title,
            suggestions=[],
            gold_codes=gold_codes,
            gold_hccs=gold_hccs,
            gold_non_codes=non_codes,
            failed=True,
        )

    unverified = sum(
        1 for s in result.suggestions for q in s.evidence if note.text[q.start : q.end] != q.text
    )
    invalid = sum(
        1
        for s in result.suggestions
        if (hit := ctx.repo.get(s.code)) is None or not hit.is_billable
    )
    return CodingNoteResult(
        note_title=note.title,
        suggestions=[(s.code, s.confidence.value, s.hcc_number) for s in result.suggestions],
        gold_codes=gold_codes,
        gold_hccs=gold_hccs,
        gold_non_codes=non_codes,
        suggestion_condition_labels=[s.condition_label for s in result.suggestions],
        dropped_quotes=result.usage.dropped_quotes,
        unverified_quotes_shown=unverified,
        invalid_codes_shown=invalid,
        duration_ms=result.usage.duration_ms,
        total_tokens=result.usage.input_tokens + result.usage.output_tokens,
    )


def evaluate_coding(
    notes: list[Note], ctx: EvalContext
) -> tuple[dict[str, object], list[dict[str, object]]]:
    note_results: list[CodingNoteResult] = []
    for note in notes:
        try:
            result: CodingResult | None = code_note(note.text, ctx.deps, ctx.config)
        except PipelineError:
            result = None
        note_results.append(_score_coding_note(note, result, ctx))

    metrics = coding_metrics(note_results)
    metrics["operational"] = operational_metrics(note_results)
    per_note = [
        {
            "note": r.note_title,
            "predicted": sorted(code for code, _, _ in r.suggestions),
            "gold": sorted(r.gold_codes),
            "failed": r.failed,
        }
        for r in note_results
    ]
    return metrics, per_note


def evaluate_audit(
    notes: list[Note], ctx: EvalContext
) -> tuple[dict[str, object], list[dict[str, object]]]:
    case_results: list[AuditCaseResult] = []
    for case in AuditCase.objects.filter(note__in=notes).select_related("note"):
        result = audit_note(case.note.text, case.submitted_codes, ctx.deps, ctx.config)
        actual = {f.submitted_code: f.verdict.value for f in result.findings if f.submitted_code}
        verdicts = {
            code: (expected, actual.get(code, "MISSING"))
            for code, expected in case.expected_verdicts.items()
        }
        case_results.append(AuditCaseResult(note_title=case.note.title, verdicts=verdicts))

    per_case: list[dict[str, object]] = [
        {"note": r.note_title, "verdicts": {k: list(v) for k, v in r.verdicts.items()}}
        for r in case_results
    ]
    return audit_metrics(case_results), per_case


def run_evaluation(split: str, mode: str, allow_unreviewed: bool) -> EvalRun:
    notes = list(
        Note.objects.filter(split=split)
        .prefetch_related("gold_labels", "gold_non_codes")
        .order_by("title")
    )
    if not notes:
        raise EvalError(f"No notes in split {split!r}. Assign splits first.")
    provisional = check_reviewed(notes, allow_unreviewed)
    ctx = build_context()

    metrics: dict[str, object] = {}
    per_note: list[dict[str, object]] = []
    if mode in ("coding", "both"):
        coding, notes_out = evaluate_coding(notes, ctx)
        metrics["coding"] = coding
        per_note.extend(notes_out)
    if mode in ("audit", "both"):
        audit, cases_out = evaluate_audit(notes, ctx)
        metrics["audit"] = audit
        per_note.extend(cases_out)

    return EvalRun.objects.create(
        split=split,
        mode=mode,
        pipeline_version=PIPELINE_VERSION,
        prompt_versions=ctx.config.prompt_versions,
        model_name=ctx.config.model_name,
        git_sha=_git_sha(),
        provisional=provisional,
        metrics=metrics,
        per_note_results=per_note,
    )
