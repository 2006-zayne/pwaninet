"""
Exceptions for Pwanimate Orchestrator.
"""


class OrchestratorError(Exception):
    """Base exception for all Pwanimate orchestration errors."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class OrchestratorValidationError(OrchestratorError):
    """Raised when an orchestration request has invalid or malformed parameters."""
    pass
