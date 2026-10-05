"""The single NinjaAPI instance. Feature apps register routers on it.

Errors share one shape everywhere: {"error": {"code": ..., "message": ...}}.
"""

from django.db import connection
from django.http import HttpRequest
from ninja import NinjaAPI, Schema
from ninja.responses import Status
from ninja.security import django_auth

from apps.accounts.api import router as accounts_router
from apps.reference.api import router as reference_router
from apps.review.api import router as review_router
from apps.runs.api import router as runs_router

# Session auth (with CSRF) on everything; the few public endpoints opt out
# with auth=None: /health, /auth/csrf, /auth/login.
api = NinjaAPI(title="Vero API", version="0.1.0", auth=django_auth)
api.add_router("", accounts_router)
api.add_router("", reference_router)
api.add_router("", runs_router)
api.add_router("", review_router)


class HealthOut(Schema):
    status: str
    database: bool
    code_set_loaded: bool


class ErrorOut(Schema):
    error: dict[str, str]


@api.get("/health", response={200: HealthOut, 503: ErrorOut}, auth=None)
def health(request: HttpRequest) -> Status[dict[str, object]]:
    try:
        connection.ensure_connection()
    except Exception:
        return Status(
            503, {"error": {"code": "DB_UNAVAILABLE", "message": "Database is unreachable."}}
        )

    from apps.reference.services import active_code_set

    if active_code_set() is None:
        return Status(
            503,
            {
                "error": {
                    "code": "NO_CODE_SET",
                    "message": "No active ICD-10-CM code set is loaded. Run `make init`.",
                }
            },
        )
    return Status(200, {"status": "ok", "database": True, "code_set_loaded": True})
