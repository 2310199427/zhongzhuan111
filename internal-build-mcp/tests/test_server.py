from __future__ import annotations

import inspect

from app import server


FORBIDDEN = {"trigger", "employeeNo", "employee_no", "userId", "operatorId", "ownerId", "creator", "submitter"}


def test_mcp_tool_functions_do_not_accept_identity_fields() -> None:
    tools = [server.preview_build, server.create_build, server.get_build_status, server.get_build_logs, server.get_build_artifacts]
    for tool in tools:
        assert FORBIDDEN.isdisjoint(inspect.signature(tool).parameters)


def test_expected_mcp_tool_functions_exist() -> None:
    assert all(callable(getattr(server, name)) for name in ("ping", "preview_build", "create_build", "get_build_status", "get_build_logs", "get_build_artifacts"))
