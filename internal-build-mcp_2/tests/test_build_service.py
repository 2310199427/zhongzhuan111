from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.actor import Actor
from app.build_service import BuildService, _build_create_payload, map_platform_status
from app.config import Settings
from app.errors import BuildNotFoundError
from app.models import BuildRequest


class StubActorProvider:
    async def get_actor(self) -> Actor:
        return Actor(name="Mock Developer", employee_no="MOCK-EMPLOYEE-000001")


def request() -> BuildRequest:
    return BuildRequest(
        repository="example-repository",
        branch="feature/example",
        cmc_version="CMC-EXAMPLE",
        inner_version_tdd="TDD-EXAMPLE",
        inner_version_fdd="FDD-EXAMPLE",
        description="Offline test build",
    )


def test_payload_uses_allowlisted_mapping_and_actor() -> None:
    payload = _build_create_payload(request(), Actor(name="Mock Developer", employee_no="MOCK-EMPLOYEE-000001"), Settings(_env_file=None))
    assert payload["trigger"] == "MOCK-EMPLOYEE-000001"
    assert payload["git_project"] == "example-repository"
    assert payload["node_branch"] == payload["git_branch"] == "feature/example"
    assert payload["point"]["inner_version_tdd"] == payload["inner_version_tdd"]
    assert payload["point"]["inner_version_fdd"] == payload["inner_version_fdd"]
    assert isinstance(payload["rtos_status"], str)
    assert isinstance(payload["qemu_flag"], bool)
    forbidden = {"employeeNo", "employee_no", "userId", "operatorId", "ownerId", "creator", "submitter"}
    assert forbidden.isdisjoint(payload)


@pytest.mark.asyncio
async def test_preview_is_structured_and_does_not_expose_payload() -> None:
    service = BuildService(Settings(_env_file=None), StubActorProvider())
    preview = await service.preview_build(request())
    assert "payload" not in preview.model_dump()
    assert "sanitized_payload" not in preview.model_dump()
    assert preview.actor_employee_no_masked != "MOCK-EMPLOYEE-000001"


@pytest.mark.asyncio
async def test_dry_run_ids_increment_and_states_are_per_task() -> None:
    service = BuildService(Settings(_env_file=None), StubActorProvider())
    first = await service.create_build(request())
    second = await service.create_build(request())
    assert first.task_id == "MOCK-TASK-000001"
    assert second.task_id == "MOCK-TASK-000002"
    assert (await service.get_build_status(first.task_id)).status == "running"
    assert (await service.get_build_status(second.task_id)).status == "running"
    assert (await service.get_build_status(first.task_id)).status == "succeeded"
    assert (await service.get_build_status(second.task_id)).status == "succeeded"


@pytest.mark.asyncio
async def test_dry_run_executes_repository_and_task_authorization(monkeypatch: pytest.MonkeyPatch) -> None:
    authorize_repository = AsyncMock()
    authorize_task_access = AsyncMock()
    monkeypatch.setattr("app.security.authorize_repository", authorize_repository)
    monkeypatch.setattr("app.security.authorize_task_access", authorize_task_access)
    service = BuildService(Settings(_env_file=None), StubActorProvider())

    task = await service.create_build(request())
    await service.get_build_status(task.task_id)

    authorize_repository.assert_awaited_once()
    authorize_task_access.assert_awaited_once()


@pytest.mark.asyncio
async def test_dry_run_logs_are_redacted_and_artifacts_are_synthetic() -> None:
    service = BuildService(Settings(_env_file=None), StubActorProvider())
    task = await service.create_build(request())
    logs = await service.get_build_logs(task.task_id)
    combined = "\n".join(logs.lines)
    assert "mock-log-secret" not in combined
    assert "[REDACTED]" in combined
    artifacts = await service.get_build_artifacts(task.task_id)
    assert artifacts.artifacts[0].startswith("https://artifacts.example.invalid/")


@pytest.mark.asyncio
async def test_unknown_dry_run_task_is_rejected() -> None:
    service = BuildService(Settings(_env_file=None), StubActorProvider())
    with pytest.raises(BuildNotFoundError):
        await service.get_build_status("MOCK-TASK-999999")


@pytest.mark.asyncio
async def test_real_mode_delegates_to_platform_client() -> None:
    client = AsyncMock()
    client.create_build.return_value = {"task_id": "TASK-EXAMPLE-001", "status": "QUEUED", "detail_url": None}
    service = BuildService(Settings(_env_file=None, dry_run=False), StubActorProvider(), client)
    result = await service.create_build(request())
    assert result.task_id == "TASK-EXAMPLE-001"
    client.create_build.assert_awaited_once()


@pytest.mark.parametrize("raw, expected", [("WAITING", "queued"), ("BUILDING", "running"), ("SUCCESS", "succeeded"), ("FAIL", "failed"), ("CANCELED", "cancelled"), ("NEW_VALUE", "unknown")])
def test_status_mapping(raw: str, expected: str) -> None:
    assert map_platform_status(raw) == expected
