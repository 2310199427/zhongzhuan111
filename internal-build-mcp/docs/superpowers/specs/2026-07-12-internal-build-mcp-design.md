# Internal Build MCP Design

## Goal

Create an offline-first Python MCP server for an internal build platform. Local development defaults to dry-run, while production integration is enabled only through explicit configuration.

## Architecture

FastMCP tools call `BuildService`. The service always validates input, resolves a trusted actor, invokes authorization hooks, constructs an allowlisted payload, and writes a redacted audit event. Only after those steps does it select the in-process dry-run store or `BuildPlatformClient`.

Dry-run task IDs are process-local, monotonically increasing values such as `MOCK-TASK-000001`. Each task has independent query state: the first status query returns `running`, later queries return `succeeded`. Preview responses contain structured fields only and never expose the platform payload.

## Security Boundaries

- MCP tool inputs never accept identity or trigger fields.
- `trigger` comes only from `ActorProvider`.
- Payloads are built with an explicit allowlist.
- Repository and task authorization hooks run in dry-run and real modes.
- Logs, errors, previews, and audit events redact secrets and mask employee numbers.
- Real HTTP is possible only when `BUILD_DRY_RUN=false`.

## Testing

Pytest covers validation, payload types, security hooks, task isolation, status transitions, audit redaction, tool signatures, and HTTP errors. HTTP tests use strict `respx` mocks; an autouse socket guard rejects all unmocked network access.

## Production Integration Points

Replace placeholder URL paths and token/identity configuration, implement the authorization hooks, confirm uncertain payload mappings, and adapt response extraction to the real platform contract.
