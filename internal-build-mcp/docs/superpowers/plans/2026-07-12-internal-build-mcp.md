# Internal Build MCP Implementation Plan

> **For agentic workers:** Implement task-by-task with TDD and verify each deliverable before continuing.

**Goal:** Build a secure, offline-testable FastMCP server that previews, creates, and queries build tasks.

**Architecture:** `BuildService` owns the common security flow and selects either an in-memory dry-run backend or an async HTTP client. Pydantic models define all public boundaries, while dedicated security and audit modules prevent secret leakage.

**Tech Stack:** Python 3.11/3.12, MCP/FastMCP, httpx, Pydantic, pydantic-settings, pytest, pytest-asyncio, respx, uv.

## Global Constraints

- `BUILD_DRY_RUN=true` by default.
- No real company values or identity fields in MCP tool inputs.
- All HTTP tests are mocked and unmocked network access fails.
- Dry-run still runs validation, identity, authorization, payload construction, and audit logic.

---

### Task 1: Models, configuration, security, and audit

Create focused tests first, verify failure, then implement `models.py`, `config.py`, `actor.py`, `security.py`, `audit.py`, and `errors.py`.

### Task 2: Platform HTTP client

Use strict `respx` tests for success, timeout, status codes, and non-JSON responses. Implement an async client with no create retry and redacted errors.

### Task 3: Build service and dry-run store

Test payload allowlisting, identity provenance, authorization calls, incrementing task IDs, per-task state, mock logs/artifacts, and real-mode delegation before implementing the service.

### Task 4: MCP server

Test the six tool signatures for forbidden identity parameters, then register thin FastMCP wrappers and stdio startup.

### Task 5: Documentation and verification

Document dry-run, real integration, Inspector, CLI Agent configuration, security risks, all settings, and troubleshooting. Run the full suite and scan the repository for leaked values and forbidden tool parameters.
