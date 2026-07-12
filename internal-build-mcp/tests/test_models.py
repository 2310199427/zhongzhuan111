from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models import BuildArtifacts, BuildLogs, BuildRequest, BuildStatus


def valid_request() -> dict[str, str]:
    return {
        "repository": "example-repository",
        "branch": "feature/example",
        "cmc_version": "CMC-EXAMPLE",
        "inner_version_tdd": "TDD-EXAMPLE",
        "inner_version_fdd": "FDD-EXAMPLE",
        "description": "Offline test build",
    }


@pytest.mark.parametrize("field", list(valid_request()))
def test_build_request_rejects_blank_fields(field: str) -> None:
    values = valid_request()
    values[field] = "   "
    with pytest.raises(ValidationError):
        BuildRequest(**values)


def test_build_request_rejects_long_description() -> None:
    with pytest.raises(ValidationError):
        BuildRequest(**(valid_request() | {"description": "x" * 501}))


@pytest.mark.parametrize("tail", [0, 2001])
def test_build_logs_rejects_invalid_tail(tail: int) -> None:
    with pytest.raises(ValidationError):
        BuildLogs(task_id="MOCK-TASK-000001", lines=[], tail=tail)


def test_build_request_has_no_identity_fields() -> None:
    forbidden = {"trigger", "employeeNo", "employee_no", "userId", "operatorId", "ownerId", "creator", "submitter"}
    assert forbidden.isdisjoint(BuildRequest.model_fields)


@pytest.mark.parametrize("model, values", [
    (BuildStatus, {"status": "unknown", "raw_status": "UNKNOWN"}),
    (BuildLogs, {"lines": []}),
    (BuildArtifacts, {"artifacts": []}),
])
def test_task_models_reject_blank_task_id(model, values) -> None:
    with pytest.raises(ValidationError):
        model(task_id=" ", **values)
