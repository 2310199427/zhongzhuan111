"""Trusted actor abstraction for identity provenance."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, field_validator

from app.config import Settings


class Actor(BaseModel):
    name: str
    employee_no: str

    @field_validator("name", "employee_no")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("actor fields must not be blank")
        return value.strip()


class ActorProvider(Protocol):
    async def get_actor(self) -> Actor: ...


class EnvironmentActorProvider:
    """仅供离线开发；生产必须替换为 CLI/SSO/JWT 等可信身份来源。"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_actor(self) -> Actor:
        return Actor(name=self._settings.actor_name, employee_no=self._settings.actor_employee_no)
