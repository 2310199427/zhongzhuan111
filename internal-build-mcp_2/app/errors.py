"""Business exceptions exposed as safe, readable MCP errors."""


class BuildMcpError(Exception):
    """Base class for expected build MCP failures."""


class AuthorizationError(BuildMcpError):
    """The current actor cannot access a repository or task."""


class BuildPlatformError(BuildMcpError):
    """The build platform returned an invalid or failed response."""


class BuildTimeoutError(BuildPlatformError):
    """The build platform request timed out."""


class BuildNotFoundError(BuildPlatformError):
    """The requested build task does not exist."""


class BuildValidationError(BuildMcpError):
    """Input or platform data failed validation."""
