"""Async HTTP adapter for the real build platform."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self
from urllib.parse import quote

import httpx

from app.config import Settings
from app.errors import AuthorizationError, BuildNotFoundError, BuildPlatformError, BuildTimeoutError
from app.security import redact_sensitive_text


class BuildPlatformClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=settings.platform_base_url,
            timeout=settings.platform_timeout_seconds,
            headers={"Authorization": f"Bearer {settings.platform_token}", "Accept": "application/json"},
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def create_build(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Deliberately no retry: retrying a timed-out create may submit duplicate builds.
        return await self._request("POST", self._settings.platform_create_path, json=payload)

    async def get_build_status(self, task_id: str) -> dict[str, Any]:
        return await self._request("GET", self._task_path(self._settings.platform_status_path, task_id))

    async def get_build_logs(self, task_id: str, tail: int = 200) -> dict[str, Any]:
        return await self._request("GET", self._task_path(self._settings.platform_logs_path, task_id), params={"tail": tail})

    async def get_build_artifacts(self, task_id: str) -> dict[str, Any]:
        return await self._request("GET", self._task_path(self._settings.platform_artifacts_path, task_id))

    @staticmethod
    def _task_path(template: str, task_id: str) -> str:
        return template.format(task_id=quote(task_id, safe=""))

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise BuildTimeoutError("Build platform request timed out; create was not retried") from exc
        except httpx.HTTPError as exc:
            raise BuildPlatformError(f"Build platform connection failed: {redact_sensitive_text(exc)}") from exc

        if response.status_code >= 400:
            self._raise_for_status(response)
        try:
            data = response.json()
        except ValueError as exc:
            raise BuildPlatformError("Build platform returned a non-JSON response") from exc
        if not isinstance(data, dict):
            raise BuildPlatformError("Build platform JSON response must be an object")
        return data

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        message = redact_sensitive_text(response.text)[:500]
        if response.status_code in {401, 403}:
            raise AuthorizationError(f"Build platform authorization failed ({response.status_code}): {message}")
        if response.status_code == 404:
            raise BuildNotFoundError(f"Build task was not found: {message}")
        if response.status_code == 400:
            raise BuildPlatformError(f"Build platform rejected the request (400): {message}")
        raise BuildPlatformError(f"Build platform error ({response.status_code}): {message}")
