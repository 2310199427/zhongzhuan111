"""Structured audit events written to stderr through the logging framework."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from typing import Any

from app.security import mask_employee_no, redact_sensitive_text


def audit_event(
    *,
    actor_name: str,
    actor_employee_no: str,
    action: str,
    repository: str | None = None,
    branch: str | None = None,
    cmc_version: str | None = None,
    task_id: str | None = None,
    success: bool,
    error_message: str | None = None,
) -> None:
    event: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "actor_name": redact_sensitive_text(actor_name),
        "actor_employee_no": mask_employee_no(actor_employee_no),
        "action": action,
        "repository": repository,
        "branch": branch,
        "cmc_version": cmc_version,
        "task_id": task_id,
        "success": success,
        "error_message": redact_sensitive_text(error_message) if error_message else None,
    }
    print(json.dumps(event, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
