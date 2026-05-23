"""Providers package — LLM and agent backends for EcoSeek."""

from .agenticplug import (
    KNOWN_TASKS,
    AgenticPlugAuthError,
    AgenticPlugClient,
    AgenticPlugError,
    AgenticPlugResult,
    resolve_connector,
)
from .hermes import (
    HermesMessage,
    HermesOrchestrationResult,
    HermesProvider,
    HermesResponse,
    HermesToolCall,
)

__all__ = [
    # AgenticPlug
    "KNOWN_TASKS",
    "AgenticPlugAuthError",
    "AgenticPlugClient",
    "AgenticPlugError",
    "AgenticPlugResult",
    "resolve_connector",
    # Hermes
    "HermesMessage",
    "HermesOrchestrationResult",
    "HermesProvider",
    "HermesResponse",
    "HermesToolCall",
]
