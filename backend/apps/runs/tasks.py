"""The background task that runs the pipeline for one run.

Takes only the run id, loads everything from the database, and is
idempotent: if the run is not queued, it exits without doing anything.
"""

import logging

from django.db import transaction
from django.tasks import task
from django.utils import timezone

from apps.llm.factory import build_llm_client
from apps.reference.services import PostgresCodeRepository
from apps.runs.models import Run
from apps.runs.services import save_coding_result
from vero_core.errors import PipelineError
from vero_core.interfaces import PipelineConfig, PipelineDeps
from vero_core.pipeline import code_note

logger = logging.getLogger(__name__)


def _config(run: Run) -> PipelineConfig:
    from django.conf import settings

    return PipelineConfig(
        model_name=settings.GEMINI_MODEL or "fake",
        retrieval_top_k=settings.VERO_RETRIEVAL_TOP_K,
    )


@task()
def process_run(run_id: str) -> None:
    claimed = Run.objects.filter(id=run_id, status=Run.Status.QUEUED).update(
        status=Run.Status.PROCESSING, started_at=timezone.now()
    )
    if not claimed:
        logger.info("run %s not queued; nothing to do", run_id)
        return
    run = Run.objects.select_related("note").get(id=run_id)

    config = _config(run)
    try:
        deps = PipelineDeps(
            llm=build_llm_client(run_id=run.id),
            codes=PostgresCodeRepository(code_set=run.code_set, hcc_model=run.hcc_model),
        )
        result = code_note(run.note.text, deps, config)
    except PipelineError as exc:
        _fail(run, exc.code, str(exc))
        return
    except Exception:
        logger.exception("run %s failed unexpectedly", run_id)
        _fail(run, "INTERNAL", "Processing failed unexpectedly. Try again.")
        return

    with transaction.atomic():
        save_coding_result(run, result)
        run.status = Run.Status.READY_FOR_REVIEW
        run.finished_at = timezone.now()
        run.duration_ms = result.usage.duration_ms
        run.input_tokens = result.usage.input_tokens
        run.output_tokens = result.usage.output_tokens
        run.dropped_quotes = result.usage.dropped_quotes
        run.model_name = config.model_name
        run.prompt_versions = config.prompt_versions
        run.save()
    logger.info("run %s ready for review (%d suggestions)", run_id, len(result.suggestions))


def _fail(run: Run, code: str, message: str) -> None:
    run.status = Run.Status.FAILED
    run.finished_at = timezone.now()
    run.error_code = code
    run.error_message = message[:300]
    run.save(update_fields=["status", "finished_at", "error_code", "error_message"])
    logger.warning("run %s failed with %s", run.id, code)
