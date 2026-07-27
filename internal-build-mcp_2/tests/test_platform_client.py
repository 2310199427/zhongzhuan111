from __future__ import annotations

import httpx
import pytest
import respx

from app.config import Settings
from app.errors import AuthorizationError, BuildNotFoundError, BuildPlatformError, BuildTimeoutError
from app.platform_client import BuildPlatformClient


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        dry_run=False,
        platform_base_url="https://build-platform.example.invalid",
        platform_create_path="/api/builds",
        platform_status_path="/api/builds/{task_id}",
        platform_logs_path="/api/builds/{task_id}/logs",
        platform_artifacts_path="/api/builds/{task_id}/artifacts",
        platform_token="placeholder-test-token",
    )


@pytest.mark.asyncio
async def test_create_build_returns_task_id(settings: Settings) -> None:
    with respx.mock(assert_all_called=True, assert_all_mocked=True) as router:
        route = router.post("https://build-platform.example.invalid/api/builds").mock(
            return_value=httpx.Response(200, json={"task_id": "TASK-EXAMPLE-001", "status": "QUEUED"})
        )
        async with BuildPlatformClient(settings) as client:
            result = await client.create_build({"git_project": "example-repository"})
    assert route.call_count == 1
    assert result["task_id"] == "TASK-EXAMPLE-001"


@pytest.mark.asyncio
async def test_create_timeout_is_not_retried(settings: Settings) -> None:
    with respx.mock(assert_all_called=True, assert_all_mocked=True) as router:
        route = router.post("https://build-platform.example.invalid/api/builds").mock(
            side_effect=httpx.ReadTimeout("timeout")
        )
        async with BuildPlatformClient(settings) as client:
            with pytest.raises(BuildTimeoutError):
                await client.create_build({"git_project": "example-repository"})
    assert route.call_count == 1


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [(400, BuildPlatformError), (401, AuthorizationError), (403, AuthorizationError), (404, BuildNotFoundError), (500, BuildPlatformError)],
)
@pytest.mark.asyncio
async def test_http_errors_are_mapped(settings: Settings, status_code: int, error_type: type[Exception]) -> None:
    with respx.mock(assert_all_called=True, assert_all_mocked=True) as router:
        router.get("https://build-platform.example.invalid/api/builds/TASK-EXAMPLE-404").mock(
            return_value=httpx.Response(status_code, text="Authorization: Bearer placeholder-secret")
        )
        async with BuildPlatformClient(settings) as client:
            with pytest.raises(error_type) as caught:
                await client.get_build_status("TASK-EXAMPLE-404")
    assert "placeholder-secret" not in str(caught.value)


@pytest.mark.asyncio
async def test_non_json_response_is_rejected(settings: Settings) -> None:
    with respx.mock(assert_all_called=True, assert_all_mocked=True) as router:
        router.get("https://build-platform.example.invalid/api/builds/TASK-EXAMPLE-001").mock(
            return_value=httpx.Response(200, text="not-json")
        )
        async with BuildPlatformClient(settings) as client:
            with pytest.raises(BuildPlatformError, match="JSON"):
                await client.get_build_status("TASK-EXAMPLE-001")
