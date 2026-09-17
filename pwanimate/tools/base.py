"""
Base contracts and abstractions for Pwanimate Domain Tools.

Domain tools expose read-only capabilities over existing PwaniNet domain
services and models. They enforce strict parameter validation, authorization
checks, zero loopback HTTP calls, and return deterministic, JSON-serializable
dictionaries.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from pwanimate.tools.exceptions import ToolValidationError


@dataclass
class ToolResult:
    """
    Standard result returned by any domain tool execution.

    Attributes:
        success: Whether the tool execution succeeded.
        data: JSON-serializable output payload (primitives, dicts, lists).
        error: Human-readable error message if execution failed.
        metadata: Execution statistics, timings, count metrics.
    """
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to a plain dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def ok(cls, data: Any, **metadata) -> "ToolResult":
        """Factory method for successful execution."""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, error: str, data: Any = None, **metadata) -> "ToolResult":
        """Factory method for failed execution."""
        return cls(success=False, data=data, error=error, metadata=metadata)


class BaseDomainTool(ABC):
    """
    Abstract base class for all Pwanimate domain tools.

    Subclasses must define `name`, `description`, `parameters_schema`,
    and implement the `execute` method.
    """
    name: str = ""
    description: str = ""
    parameters_schema: Dict[str, Any] = {}

    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """
        Validate incoming keyword arguments against the tool's schema.
        Raises ToolValidationError if required parameters are missing or invalid.
        """
        schema = self.parameters_schema or {}
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Check required fields
        for field_name in required:
            if field_name not in kwargs or kwargs[field_name] is None:
                raise ToolValidationError(
                    f"Missing required parameter '{field_name}'",
                    tool_name=self.name,
                )

        validated = {}
        for k, v in kwargs.items():
            if k in properties:
                validated[k] = v
        return validated

    @abstractmethod
    def execute(self, user: Any, **kwargs) -> ToolResult:
        """
        Execute the domain tool on behalf of the user.

        Args:
            user: Authenticated or anonymous Django user model instance.
            **kwargs: Validated input parameters.

        Returns:
            ToolResult containing JSON-serializable payload or error.
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Return tool metadata and schema representation."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
        }
