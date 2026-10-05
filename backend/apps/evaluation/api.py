import uuid
from datetime import datetime

from django.http import HttpRequest
from ninja import Router, Schema
from ninja.responses import Status

from apps.accounts.auth import is_admin
from apps.evaluation.models import EvalRun

router = Router(tags=["evaluation"])


class EvalRunListOut(Schema):
    id: uuid.UUID
    created_at: datetime
    split: str
    mode: str
    model_name: str
    provisional: bool


class EvalRunDetailOut(EvalRunListOut):
    pipeline_version: str
    prompt_versions: dict[str, str]
    git_sha: str
    metrics: dict[str, object]
    per_note_results: list[dict[str, object]]


class ErrorOut(Schema):
    error: dict[str, str]


FORBIDDEN = {"error": {"code": "ADMIN_ONLY", "message": "Evaluation is admin-only."}}


@router.get("/eval/runs", response={200: list[EvalRunListOut], 403: ErrorOut})
def list_eval_runs(request: HttpRequest) -> Status[object]:
    if not is_admin(request):
        return Status(403, FORBIDDEN)
    return Status(
        200,
        [
            EvalRunListOut(
                id=run.id,
                created_at=run.created_at,
                split=run.split,
                mode=run.mode,
                model_name=run.model_name,
                provisional=run.provisional,
            )
            for run in EvalRun.objects.all()[:50]
        ],
    )


@router.get("/eval/runs/{run_id}", response={200: EvalRunDetailOut, 403: ErrorOut, 404: ErrorOut})
def get_eval_run(request: HttpRequest, run_id: uuid.UUID) -> Status[object]:
    if not is_admin(request):
        return Status(403, FORBIDDEN)
    run = EvalRun.objects.filter(id=run_id).first()
    if run is None:
        return Status(404, {"error": {"code": "NOT_FOUND", "message": "Unknown eval run."}})
    return Status(
        200,
        EvalRunDetailOut(
            id=run.id,
            created_at=run.created_at,
            split=run.split,
            mode=run.mode,
            model_name=run.model_name,
            provisional=run.provisional,
            pipeline_version=run.pipeline_version,
            prompt_versions=run.prompt_versions,
            git_sha=run.git_sha,
            metrics=run.metrics,
            per_note_results=run.per_note_results,
        ),
    )
