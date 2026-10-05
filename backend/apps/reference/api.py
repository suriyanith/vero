from django.http import HttpRequest
from ninja import Router, Schema
from ninja.responses import Status

from apps.reference.services import PostgresCodeRepository, active_code_set

router = Router(tags=["codes"])


class CodeOut(Schema):
    display_code: str
    description: str
    is_billable: bool
    hcc_number: int | None
    hcc_label: str | None


class CodeDetailOut(CodeOut):
    category: str
    notes: dict[str, list[str]]


class ErrorOut(Schema):
    error: dict[str, str]


@router.get("/codes/search", response=list[CodeOut])
def search_codes(request: HttpRequest, q: str, limit: int = 20) -> list[CodeOut]:
    limit = max(1, min(limit, 50))
    repo = PostgresCodeRepository()
    return [
        CodeOut(
            display_code=hit.display_code,
            description=hit.description,
            is_billable=hit.is_billable,
            hcc_number=hit.hcc_number,
            hcc_label=hit.hcc_label,
        )
        for hit in repo.search(q, limit=limit)
    ]


@router.get("/codes/{display_code}", response={200: CodeDetailOut, 404: ErrorOut})
def get_code(request: HttpRequest, display_code: str) -> Status[object]:
    if active_code_set() is None:
        return Status(404, {"error": {"code": "NO_CODE_SET", "message": "No code set is loaded."}})
    hit = PostgresCodeRepository().get(display_code)
    if hit is None:
        return Status(
            404, {"error": {"code": "CODE_NOT_FOUND", "message": f"Unknown code {display_code}."}}
        )
    return Status(
        200,
        CodeDetailOut(
            display_code=hit.display_code,
            description=hit.description,
            is_billable=hit.is_billable,
            hcc_number=hit.hcc_number,
            hcc_label=hit.hcc_label,
            category=hit.category,
            notes=hit.notes,
        ),
    )
