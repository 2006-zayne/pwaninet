"""
Pwanimate Tool Adapters, Registry & Deterministic Router.

Exposes domain tools, deterministic router, context adapters, and runtime
execution abstractions for Pwanimate.
"""

from pwanimate.tools.base import BaseDomainTool, ToolResult
from pwanimate.tools.exceptions import (
    ToolError,
    ToolNotFoundError,
    ToolValidationError,
    ToolPermissionError,
    ToolExecutionError,
)
from pwanimate.tools.registry import ToolRegistry, get_default_tool_registry
from pwanimate.tools.router import ToolRoute, ToolRouter
from pwanimate.tools.adapter import (
    tool_result_to_context_items,
    build_tool_context_package,
)

__all__ = [
    "BaseDomainTool",
    "ToolResult",
    "ToolRegistry",
    "get_default_tool_registry",
    "ToolRoute",
    "ToolRouter",
    "tool_result_to_context_items",
    "build_tool_context_package",
    "ToolError",
    "ToolNotFoundError",
    "ToolValidationError",
    "ToolPermissionError",
    "ToolExecutionError",
]
