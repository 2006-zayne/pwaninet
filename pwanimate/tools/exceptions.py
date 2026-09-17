"""
Tool Exceptions for Pwanimate Domain Tools.

Defines standardized exceptions for domain tool lookup, parameter validation,
authorization, and runtime execution.
"""


class ToolError(Exception):
    """Base exception for all Pwanimate tool operations."""
    def __init__(self, message: str, tool_name: str = "", details: dict = None):
        super().__init__(message)
        self.message = message
        self.tool_name = tool_name
        self.details = details or {}

    def __str__(self):
        prefix = f"[{self.tool_name}] " if self.tool_name else ""
        return f"{prefix}{self.message}"


class ToolNotFoundError(ToolError):
    """Raised when an requested tool is not found in the registry."""
    pass


class ToolValidationError(ToolError):
    """Raised when tool parameters fail validation constraints."""
    pass


class ToolPermissionError(ToolError):
    """Raised when a user lacks permission to access domain resources via a tool."""
    pass


class ToolExecutionError(ToolError):
    """Raised when an unhandled error occurs during tool execution."""
    pass
