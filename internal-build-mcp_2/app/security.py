"""Redaction and authorization extension points."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.actor import Actor


_HEADER_SECRET = re.compile(r"(?i)\b(authorization|cookie|password|token)\b\s*[:=]\s*([^\s,;]+(?:\s+[^\s,;]+)?)")
_BEARER_SECRET = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")


def redact_sensitive_text(value: object) -> str:
    text = str(value)
    text = _BEARER_SECRET.sub("Bearer [REDACTED]", text)
    return _HEADER_SECRET.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)


def mask_employee_no(employee_no: str) -> str:
    """Reveal only a tiny prefix so the complete identifier cannot be recovered."""
    if not employee_no:
        return "***"
    visible = employee_no[:2] if len(employee_no) > 2 else ""
    return f"{visible}***"


async def authorize_repository(actor: "Actor", repository: str) -> None:
    # TODO(公司接入)：当前为允许全部的占位实现，生产必须查询真实代码库 ACL。
    del actor, repository


async def authorize_task_access(actor: "Actor", task_id: str) -> None:
    # TODO(公司接入)：生产必须验证当前 Actor 有权读取该 task_id 的状态、日志和产物。
    del actor, task_id
