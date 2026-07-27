"""FastMCP stdio entry point with intentionally thin tool wrappers."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.actor import EnvironmentActorProvider
from app.build_service import BuildService
from app.config import Settings
from app.models import BuildRequest
from app.platform_client import BuildPlatformClient


settings = Settings()
platform_client = None if settings.dry_run else BuildPlatformClient(settings)
service = BuildService(settings, EnvironmentActorProvider(settings), platform_client)
mcp = FastMCP("Internal Build MCP")


@mcp.tool()
async def ping() -> dict[str, object]:
    """Check that the MCP server process is responsive."""
    return {"ok": True, "service": "internal-build-mcp", "dry_run": settings.dry_run}


def _request(repository: str, branch: str, cmc_version: str, inner_version_tdd: str, inner_version_fdd: str, description: str) -> BuildRequest:
    return BuildRequest(repository=repository, branch=branch, cmc_version=cmc_version, inner_version_tdd=inner_version_tdd, inner_version_fdd=inner_version_fdd, description=description)


@mcp.tool()
async def preview_build(repository: str, branch: str, cmc_version: str, inner_version_tdd: str, inner_version_fdd: str, description: str) -> dict[str, object]:
    """Validate and preview a build without exposing the platform payload."""
    return (await service.preview_build(_request(repository, branch, cmc_version, inner_version_tdd, inner_version_fdd, description))).model_dump()


@mcp.tool()
async def create_build(repository: str, branch: str, cmc_version: str, inner_version_tdd: str, inner_version_fdd: str, description: str) -> dict[str, object]:
    """Create a dry-run or real build after identity and authorization checks."""
    return (await service.create_build(_request(repository, branch, cmc_version, inner_version_tdd, inner_version_fdd, description))).model_dump()


@mcp.tool()
async def get_build_status(task_id: str) -> dict[str, object]:
    """Query a build task status after task access authorization."""
    return (await service.get_build_status(task_id)).model_dump()


@mcp.tool()
async def get_build_logs(task_id: str, tail: int = 200) -> dict[str, object]:
    """Return redacted build logs."""
    return (await service.get_build_logs(task_id, tail)).model_dump()


@mcp.tool()
async def get_build_artifacts(task_id: str) -> dict[str, object]:
    """Return build artifact URLs after task access authorization."""
    return (await service.get_build_artifacts(task_id)).model_dump()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
