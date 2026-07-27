"""Environment-backed settings. All defaults are intentionally synthetic."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BUILD_", env_file=".env", extra="ignore")

    dry_run: bool = True
    platform_base_url: str = "https://build-platform.example.invalid"
    platform_create_api_name: str = "CREATE_BUILD_API"
    platform_status_api_name: str = "QUERY_BUILD_STATUS_API"
    platform_logs_api_name: str = "QUERY_BUILD_LOGS_API"
    platform_artifacts_api_name: str = "QUERY_BUILD_ARTIFACTS_API"
    platform_create_path: str = "/TODO/CREATE_BUILD_API"
    platform_status_path: str = "/TODO/QUERY_BUILD_STATUS_API/{task_id}"
    platform_logs_path: str = "/TODO/QUERY_BUILD_LOGS_API/{task_id}"
    platform_artifacts_path: str = "/TODO/QUERY_BUILD_ARTIFACTS_API/{task_id}"
    platform_token: str = Field(default="replace-with-placeholder-token", repr=False)
    platform_timeout_seconds: float = Field(default=30.0, gt=0)

    default_node_branch_mode: str = "same_as_git_branch"
    default_inner_version_ruet: str = "<INNER_VERSION_RUET>"
    default_git_marp_branch: str = "<GIT_MARP_BRANCH>"
    default_git_marp_no: str = "<GIT_MARP_COMMIT_ID>"
    default_unlock_uart_statue: str = "<UNLOCK_UART_STATUE>"
    default_cbb_status: str = ""
    default_rtos_status: str = "false"
    default_tailor_status: str = "false"
    default_compile_dpd_flag: str = "false"
    default_fpga_status: str = "false"
    default_git_branch_dpd: str = "<GIT_BRANCH_DPD>"
    default_pck_model: str = "<PCK_MODEL>"
    default_project_name: str = "<PROJECT_NAME>"
    default_env_id_marp: str = ""
    default_env_id_rtos_marp: str = ""
    default_qemu_flag: bool = False
    default_ruet_whitebox_flag: str = "0"
    default_uploading_external_file_flag: bool = True
    default_cbb_bsp_type: str = ""

    actor_name: str = "Mock Developer"
    actor_employee_no: str = Field(default="MOCK-EMPLOYEE-000001", repr=False)
