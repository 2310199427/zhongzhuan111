from __future__ import annotations

from app.security import mask_employee_no, redact_sensitive_text


def test_redact_sensitive_text_removes_common_secret_forms() -> None:
    text = "Authorization: Bearer mock-secret Cookie=session=mock-cookie Password=mock-password token=mock-token"
    redacted = redact_sensitive_text(text)
    for secret in ("mock-secret", "mock-cookie", "mock-password", "mock-token"):
        assert secret not in redacted
    assert "[REDACTED]" in redacted


def test_mask_employee_no_never_returns_complete_value() -> None:
    assert mask_employee_no("MOCK-EMPLOYEE-000001") != "MOCK-EMPLOYEE-000001"
    assert "000001" not in mask_employee_no("MOCK-EMPLOYEE-000001")
