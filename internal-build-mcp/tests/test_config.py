from __future__ import annotations

from app.config import Settings


def test_dry_run_defaults_true(monkeypatch) -> None:
    monkeypatch.delenv("BUILD_DRY_RUN", raising=False)
    assert Settings(_env_file=None).dry_run is True


def test_string_and_boolean_payload_defaults_keep_types() -> None:
    settings = Settings(_env_file=None)
    assert settings.default_rtos_status == "false"
    assert settings.default_qemu_flag is False
    assert settings.default_uploading_external_file_flag is True
