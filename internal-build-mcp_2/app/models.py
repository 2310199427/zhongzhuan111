"""Validated models used at MCP and service boundaries."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BuildRequest(StrictModel):
    repository: str
    branch: str
    cmc_version: str
    inner_version_tdd: str
    inner_version_fdd: str
    description: str = Field(max_length=500)

    @field_validator("repository", "branch", "cmc_version", "inner_version_tdd", "inner_version_fdd", "description")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class BuildPreview(StrictModel):
    repository: str
    branch: str
    cmc_version: str
    inner_version_tdd: str
    inner_version_fdd: str
    description: str
    actor_name: str
    actor_employee_no_masked: str
    dry_run: bool
    warnings: list[str] = Field(default_factory=list)


class BuildResult(StrictModel):
    task_id: str
    status: str
    detail_url: str | None = None
    dry_run: bool

    @field_validator("task_id")
    @classmethod
    def reject_blank_task_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("task_id must not be blank")
        return value.strip()


class TaskModel(StrictModel):
    task_id: str

    @field_validator("task_id")
    @classmethod
    def reject_blank_task_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("task_id must not be blank")
        return value.strip()


class BuildStatus(TaskModel):
    status: Literal["queued", "running", "succeeded", "failed", "cancelled", "unknown"]
    raw_status: str
    detail_url: str | None = None


class BuildLogs(TaskModel):
    lines: list[str]
    tail: int = Field(default=200, ge=1, le=2000)


class BuildArtifacts(TaskModel):
    artifacts: list[str]


JsonObject = dict[str, Any]
