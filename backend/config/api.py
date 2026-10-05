"""The single NinjaAPI instance. Feature apps register routers on it.

Errors share one shape everywhere: {"error": {"code": ..., "message": ...}}.
"""

from django.db import connection
from django.http import HttpRequest
from ninja import NinjaAPI, Schema

api = NinjaAPI(title="Vero API", version="0.1.0")


class HealthOut(Schema):
    status: str
    database: bool
    # Phase 1 will also require an active ICD-10 code set to be loaded.
    code_set_loaded: bool


class ErrorOut(Schema):
    error: dict[str, str]


@api.get("/health", response={200: HealthOut, 503: ErrorOut}, auth=None)
def health(request: HttpRequest) -> tuple[int, dict[str, object]]:
    try:
        connection.ensure_connection()
    except Exception:
        return 503, {"error": {"code": "DB_UNAVAILABLE", "message": "Database is unreachable."}}
    return 200, {"status": "ok", "database": True, "code_set_loaded": False}
