"""Business orchestration shared by dry-run and real platform modes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app import security
from app.actor import Actor, ActorProvider
from app.audit import audit_event
from app.config import Settings
from app.errors import BuildMcpError, BuildNotFoundError, BuildPlatformError, BuildValidationError
from app.models import BuildArtifacts, BuildLogs, BuildPreview, BuildRequest, BuildResult, BuildStatus
from app.security import mask_employee_no, redact_sensitive_text


class PlatformClient(Protocol):
    async def create_build(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def get_build_status(self, task_id: str) -> dict[str, Any]: ...
    async def get_build_logs(self, task_id: str, tail: int = 200) -> dict[str, Any]: ...
    async def get_build_artifacts(self, task_id: str) -> dict[str, Any]: ...


@dataclass
class _MockTask:
    payload: dict[str, Any]
    status_queries: int = 0


STATUS_MAP = {
    "WAITING": "queued", "QUEUED": "queued", "PENDING": "queued",
    "BUILDING": "running", "RUNNING": "running",
    "SUCCESS": "succeeded", "SUCCEEDED": "succeeded",
    "FAILED": "failed", "FAIL": "failed",
    "CANCELLED": "cancelled", "CANCELED": "cancelled",
}


def map_platform_status(raw_status: object) -> str:
    return STATUS_MAP.get(str(raw_status).strip().upper(), "unknown")


def _build_create_payload(request: BuildRequest, actor: Actor, settings: Settings) -> dict[str, Any]:
    """使用显式白名单构造 payload，绝不透传调用方字典。"""
    # TODO(公司接入)：确认 node_branch 是否永远等于 git_branch。
    # TODO(公司接入)：接口明确后，优先从平台默认配置接口动态获取 git_marp_no。
    # TODO(公司接入)：确认 pck_model/project_name 是否需要按 repository 映射。
    return {
        "op_flag": "Create",
        "git_project": request.repository,
        "node_branch": request.branch,
        "git_branch": request.branch,
        "cmc_ver_info": request.cmc_version,
        "inner_version_tdd": request.inner_version_tdd,
        "inner_version_fdd": request.inner_version_fdd,
        "inner_version_ruet": settings.default_inner_version_ruet,
        "git_marp_branch": settings.default_git_marp_branch,
        "git_marp_no": settings.default_git_marp_no,
        # 字段名看似拼写有误，但必须保持平台原始契约，不能擅自改成 status。
        "unlock_uart_statue": settings.default_unlock_uart_statue,
        "cbb_status": settings.default_cbb_status,
        "rtos_status": settings.default_rtos_status,
        "tailor_status": settings.default_tailor_status,
        "compile_dpd_flag": settings.default_compile_dpd_flag,
        "fpga_status": settings.default_fpga_status,
        "git_branch_dpd": settings.default_git_branch_dpd,
        "pck_model": settings.default_pck_model,
        "project_name": settings.default_project_name,
        # 安全边界：trigger 只能来自可信 ActorProvider，不能来自 MCP Tool 参数。
        "trigger": actor.employee_no,
        "remark": request.description,
        "env_id_marp": settings.default_env_id_marp,
        "env_id_rtos_marp": settings.default_env_id_rtos_marp,
        "qemu_flag": settings.default_qemu_flag,
        "ruet_whitebox_flag": settings.default_ruet_whitebox_flag,
        "uploading_external_file_flag": settings.default_uploading_external_file_flag,
        "point": {"inner_version_tdd": request.inner_version_tdd, "inner_version_fdd": request.inner_version_fdd},
        "cbb_bsp_type": settings.default_cbb_bsp_type,
        "start_type": "New",
    }


class BuildService:
    def __init__(self, settings: Settings, actor_provider: ActorProvider, platform_client: PlatformClient | None = None) -> None:
        self._settings = settings
        self._actor_provider = actor_provider
        self._platform_client = platform_client
        self._mock_sequence = 0
        self._mock_tasks: dict[str, _MockTask] = {}

    async def preview_build(self, request: BuildRequest) -> BuildPreview:
        actor = await self._actor_provider.get_actor()
        try:
            await security.authorize_repository(actor, request.repository)
            _build_create_payload(request, actor, self._settings)  # Validate the same mapping path as create.
            result = BuildPreview(
                **request.model_dump(), actor_name=actor.name,
                actor_employee_no_masked=mask_employee_no(actor.employee_no), dry_run=self._settings.dry_run,
                warnings=["node_branch currently follows branch; confirm this mapping before production"],
            )
            self._audit(actor, "preview_build", request=request, success=True)
            return result
        except Exception as exc:
            self._audit(actor, "preview_build", request=request, success=False, error=exc)
            raise

    async def create_build(self, request: BuildRequest) -> BuildResult:
        actor = await self._actor_provider.get_actor()
        try:
            await security.authorize_repository(actor, request.repository)
            payload = _build_create_payload(request, actor, self._settings)
            if self._settings.dry_run:
                self._mock_sequence += 1
                task_id = f"MOCK-TASK-{self._mock_sequence:06d}"
                self._mock_tasks[task_id] = _MockTask(payload=payload)
                result = BuildResult(task_id=task_id, status="queued", detail_url=f"https://build-detail.example.invalid/tasks/{task_id}", dry_run=True)
            else:
                client = self._require_client()
                data = await client.create_build(payload)
                task_id = self._required_string(data, "task_id")
                result = BuildResult(task_id=task_id, status=map_platform_status(data.get("status")), detail_url=self._optional_string(data.get("detail_url")), dry_run=False)
            self._audit(actor, "create_build", request=request, task_id=result.task_id, success=True)
            return result
        except Exception as exc:
            self._audit(actor, "create_build", request=request, success=False, error=exc)
            raise

    async def get_build_status(self, task_id: str) -> BuildStatus:
        task_id = self._validate_task_id(task_id)
        actor = await self._actor_provider.get_actor()
        try:
            await security.authorize_task_access(actor, task_id)
            if self._settings.dry_run:
                task = self._get_mock_task(task_id)
                task.status_queries += 1
                raw = "RUNNING" if task.status_queries == 1 else "SUCCEEDED"
                detail_url = f"https://build-detail.example.invalid/tasks/{task_id}"
            else:
                data = await self._require_client().get_build_status(task_id)
                raw = str(data.get("status", "UNKNOWN"))
                detail_url = self._optional_string(data.get("detail_url"))
            result = BuildStatus(task_id=task_id, status=map_platform_status(raw), raw_status=raw, detail_url=detail_url)
            self._audit(actor, "get_build_status", task_id=task_id, success=True)
            return result
        except Exception as exc:
            self._audit(actor, "get_build_status", task_id=task_id, success=False, error=exc)
            raise

    async def get_build_logs(self, task_id: str, tail: int = 200) -> BuildLogs:
        task_id = self._validate_task_id(task_id)
        if not 1 <= tail <= 2000:
            raise BuildValidationError("tail must be between 1 and 2000")
        actor = await self._actor_provider.get_actor()
        try:
            await security.authorize_task_access(actor, task_id)
            if self._settings.dry_run:
                self._get_mock_task(task_id)
                raw_lines = ["Mock build started", "Authorization: Bearer mock-log-secret", "Cookie=session=mock-log-cookie", "Password=mock-log-password", "Mock build completed"]
            else:
                data = await self._require_client().get_build_logs(task_id, tail)
                raw = data.get("lines", data.get("logs", []))
                raw_lines = raw if isinstance(raw, list) else str(raw).splitlines()
            lines = [redact_sensitive_text(line) for line in raw_lines][-tail:]
            result = BuildLogs(task_id=task_id, lines=lines, tail=tail)
            self._audit(actor, "get_build_logs", task_id=task_id, success=True)
            return result
        except Exception as exc:
            self._audit(actor, "get_build_logs", task_id=task_id, success=False, error=exc)
            raise

    async def get_build_artifacts(self, task_id: str) -> BuildArtifacts:
        task_id = self._validate_task_id(task_id)
        actor = await self._actor_provider.get_actor()
        try:
            await security.authorize_task_access(actor, task_id)
            if self._settings.dry_run:
                self._get_mock_task(task_id)
                artifacts = [f"https://artifacts.example.invalid/{task_id}/mock-package.zip"]
            else:
                data = await self._require_client().get_build_artifacts(task_id)
                raw = data.get("artifacts", [])
                if not isinstance(raw, list):
                    raise BuildPlatformError("Platform artifacts field must be a list")
                artifacts = [redact_sensitive_text(item) for item in raw]
            result = BuildArtifacts(task_id=task_id, artifacts=artifacts)
            self._audit(actor, "get_build_artifacts", task_id=task_id, success=True)
            return result
        except Exception as exc:
            self._audit(actor, "get_build_artifacts", task_id=task_id, success=False, error=exc)
            raise

    def _get_mock_task(self, task_id: str) -> _MockTask:
        try:
            return self._mock_tasks[task_id]
        except KeyError as exc:
            raise BuildNotFoundError(f"Mock build task not found: {task_id}") from exc

    def _require_client(self) -> PlatformClient:
        if self._platform_client is None:
            raise BuildPlatformError("Real mode requires a BuildPlatformClient")
        return self._platform_client

    @staticmethod
    def _validate_task_id(task_id: str) -> str:
        if not isinstance(task_id, str) or not task_id.strip():
            raise BuildValidationError("task_id must not be blank")
        return task_id.strip()

    @staticmethod
    def _required_string(data: dict[str, Any], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise BuildPlatformError(f"Platform response is missing {key}")
        return value.strip()

    @staticmethod
    def _optional_string(value: object) -> str | None:
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _audit(actor: Actor, action: str, *, request: BuildRequest | None = None, task_id: str | None = None, success: bool, error: Exception | None = None) -> None:
        audit_event(actor_name=actor.name, actor_employee_no=actor.employee_no, action=action,
                    repository=request.repository if request else None, branch=request.branch if request else None,
                    cmc_version=request.cmc_version if request else None, task_id=task_id, success=success,
                    error_message=str(error) if error else None)
