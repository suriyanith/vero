from django.http import HttpRequest
from ninja import Router

from apps.dashboard.services import summary

router = Router(tags=["dashboard"])

ALLOWED_WINDOWS = (7, 30, 90)


@router.get("/dashboard/summary")
def dashboard_summary(request: HttpRequest, days: int = 30) -> dict[str, object]:
    if days not in ALLOWED_WINDOWS:
        days = 30
    return summary(days)
