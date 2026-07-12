from __future__ import annotations

import json

from app.audit import audit_event


def test_audit_event_masks_employee_and_redacts_error(capsys) -> None:
    audit_event(
        actor_name="Mock Developer",
        actor_employee_no="MOCK-EMPLOYEE-000001",
        action="create_build",
        repository="example-repository",
        success=False,
        error_message="Authorization: Bearer mock-secret",
    )
    output = capsys.readouterr()
    assert output.out == ""
    event = json.loads(output.err)
    assert event["actor_employee_no"] != "MOCK-EMPLOYEE-000001"
    assert "mock-secret" not in event["error_message"]
