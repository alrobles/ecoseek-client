"""Provider abstractions for ecoseek-client.

All providers follow a common interface so the AAR loop and CLI
can use them interchangeably.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TaskResult:
    """Result of a task dispatched to a provider."""

    task_id: str
    status: str  # "accepted", "running", "completed", "failed"
    output: Optional[str] = None
    error: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.raw is None:
            self.raw = {}


class BaseProvider(ABC):
    """Abstract base for all model/agent providers."""

    name: str = "base"

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the provider is reachable."""

    @abstractmethod
    def send_task(self, task: str, **kwargs) -> TaskResult:
        """Send a task and return the result."""

    def get_task_status(self, task_id: str) -> TaskResult:
        """Poll for task status. Default: returns unknown."""
        return TaskResult(task_id=task_id, status="unknown")
