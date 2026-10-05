from collections.abc import Iterator
from typing import Any

import pytest
from django.core.cache import cache
from django.test import Client

from apps.accounts.models import User
from tests.test_loaders import load_fixture_code_set, load_fixture_hcc_map
from vero_core.fake_llm import FakeLLMClient
from vero_core.schemas import (
    Certainty,
    CodeChoice,
    ConditionSelection,
    ConditionStatus,
    ExtractedCondition,
    ExtractedQuote,
    ExtractionResult,
    Meat,
    SelectionResult,
)


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    # The locmem cache (login rate limiting) survives across tests otherwise.
    cache.clear()


@pytest.fixture
def user(db: None) -> User:
    return User.objects.create_user(username="coder1", password="pw", role=User.Role.CODER)


@pytest.fixture
def admin_user(db: None) -> User:
    return User.objects.create_user(
        username="admin1", password="pw", role=User.Role.ADMIN, is_staff=True
    )


@pytest.fixture
def client(user: User) -> Client:
    """A logged-in coder client; the API requires a session everywhere."""
    logged_in = Client()
    logged_in.force_login(user)
    return logged_in


@pytest.fixture
def anon_client() -> Client:
    return Client()


# ---- shared pipeline fixture: fixture code set + canned LLM responses ----

NOTE_TEXT = (
    "HPI: 72-year-old with type 2 diabetes and CKD stage 3a.\n"
    "Assessment:\n"
    "1. Type 2 diabetes with CKD stage 3a - continue metformin, eGFR stable at 52.\n"
    "2. Rule out heart failure. Order echocardiogram.\n"
)

EXTRACTION = ExtractionResult(
    conditions=[
        ExtractedCondition(
            label="type 2 diabetes mellitus with diabetic chronic kidney disease",
            status=ConditionStatus.ACTIVE,
            quotes=[
                ExtractedQuote(
                    text="Type 2 diabetes with CKD stage 3a - continue metformin",
                    meat=[Meat.TREAT, Meat.ASSESS],
                )
            ],
            specificity_details=[],
        ),
        ExtractedCondition(
            label="chronic kidney disease stage 3a",
            status=ConditionStatus.ACTIVE,
            quotes=[ExtractedQuote(text="eGFR stable at 52", meat=[Meat.EVALUATE])],
            specificity_details=[],
        ),
        ExtractedCondition(
            label="heart failure",
            status=ConditionStatus.UNCERTAIN,
            quotes=[ExtractedQuote(text="Rule out heart failure", meat=[])],
            specificity_details=[],
        ),
    ]
)

SELECTION = SelectionResult(
    selections=[
        ConditionSelection(
            condition_index=1,
            codes=[CodeChoice(code="E11.22", rationale="combination code applies")],
            no_fit=False,
            specificity_flags=[],
            certainty=Certainty.HIGH,
        ),
        ConditionSelection(
            condition_index=2,
            codes=[CodeChoice(code="N18.31", rationale="stage 3a documented")],
            no_fit=False,
            specificity_flags=[],
            certainty=Certainty.HIGH,
        ),
    ]
)


@pytest.fixture
def pipeline_env(db: None, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fixture code set + a canned LLM so runs process fully offline."""
    load_fixture_code_set()
    load_fixture_hcc_map()
    monkeypatch.setattr(
        "apps.runs.tasks.build_llm_client",
        lambda run_id=None: FakeLLMClient(responses={"extract": EXTRACTION, "select": SELECTION}),
    )
    yield


def post_run(
    client: Client, django_capture_on_commit_callbacks: Any, payload: dict[str, Any]
) -> Any:
    # The task is enqueued on commit; executing the callbacks runs it
    # synchronously through the immediate backend.
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post("/api/runs", payload, content_type="application/json")
    return response
