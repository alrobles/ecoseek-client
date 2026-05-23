"""HermesProvider — scientific agent provider backed by Hermes orchestrator.

Routes through AgenticPlug → Hermes for multi-provider LLM execution,
tool calling, memory, skills, and AAR-aware reasoning.

Architecture:
  ecoseek-client → AgenticPlug (auth, rate limit, audit)
                       → Hermes (:8642, OpenAI-compatible)
                            ├── DeepSeek v4 Pro (primary)
                            ├── OpenCode Go (fallback)
                            ├── Skills (ecoseek-orchestrator, ecocoder, ecoagent)
                            ├── Memory (ecosystem knowledge)
                            └── Tools (terminal, web, GitHub, delegate_task)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .agenticplug import AgenticPlugClient, AgenticPlugResult


# ── Data types ─────────────────────────────────────────────────────────


@dataclass
class HermesMessage:
    """A message in a Hermes conversation."""

    role: str  # "user", "assistant", "system", "tool"
    content: str


@dataclass
class HermesToolCall:
    """A tool call requested by Hermes."""

    id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HermesResponse:
    """Response from a Hermes chat completion."""

    message: HermesMessage
    tool_calls: List[HermesToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HermesOrchestrationResult:
    """Result of an orchestration task routed through Hermes."""

    task_id: str
    status: str  # "accepted", "running", "completed", "failed"
    result: Optional[Dict[str, Any]] = None
    plan: Optional[Dict[str, Any]] = None
    workers: List[Dict[str, Any]] = field(default_factory=list)
    review: Optional[Dict[str, Any]] = None
    report: Optional[str] = None
    error: Optional[str] = None
    elapsed_ms: float = 0.0


# ── Provider ───────────────────────────────────────────────────────────


class HermesProvider:
    """Scientific agent provider backed by Hermes via AgenticPlug.

    Hermes is NOT just an LLM — it's a full agent with:
    - Multi-provider LLM (DeepSeek v4 Pro primary, OpenCode Go fallback)
    - Skills (ecoseek-orchestrator, ecocoder-worker, ecoagent-worker, reviewer-worker)
    - Memory (ecosystem knowledge across sessions)
    - Tools (terminal, web_search, GitHub, delegate_task, session_search)
    - Plan mode (task decomposition)
    - Delegate (parallel subagents)

    Usage:
        provider = HermesProvider()
        result = provider.orchestrate("Run SDM for jaguar in Yucatan")
        print(result.report)
    """

    def __init__(
        self,
        client: Optional[AgenticPlugClient] = None,
        timeout: int = 300,
    ):
        self._client = client or AgenticPlugClient()
        self.timeout = timeout

    @property
    def client(self) -> AgenticPlugClient:
        return self._client

    # ── Orchestration ─────────────────────────────────────────────────

    def orchestrate(
        self,
        task: str,
        mode: str = "ecoSeek",
        context: Optional[Dict[str, Any]] = None,
        wait: bool = True,
    ) -> HermesOrchestrationResult:
        """Send a task to Hermes for full orchestration.

        Hermes receives the task, plans it, delegates to workers in parallel,
        reviews results, and returns a report.

        Args:
            task: The task description in natural language.
            mode: "ecoSeek" for full orchestration, "diy" for direct.
            context: Optional context (files, constraints, previous results).
            wait: If True, poll until completion. If False, return immediately.

        Returns:
            HermesOrchestrationResult with task_id, status, plan, workers, review, report.
        """
        t0 = time.monotonic()

        body: Dict[str, Any] = {"task": task, "mode": mode}
        if context:
            body["context"] = context

        # Dispatch through AgenticPlug → connector → Hermes bridge
        result = self._client._request(
            "POST",
            "/v1/orchestrate",
            auth=True,
            json_body=body,
        )

        if not result.success:
            elapsed = (time.monotonic() - t0) * 1000
            return HermesOrchestrationResult(
                task_id="",
                status="failed",
                error=result.error,
                elapsed_ms=elapsed,
            )

        data = result.data or {}
        task_id = data.get("task_id", "")

        if not wait or not task_id:
            elapsed = (time.monotonic() - t0) * 1000
            return HermesOrchestrationResult(
                task_id=task_id,
                status=data.get("status", "accepted"),
                elapsed_ms=elapsed,
            )

        # Poll until completion
        return self._poll_until_done(task_id, t0)

    def _poll_until_done(
        self,
        task_id: str,
        t0: float,
        poll_interval: float = 3.0,
    ) -> HermesOrchestrationResult:
        """Poll task status until completion or timeout."""
        deadline = time.monotonic() + self.timeout

        while time.monotonic() < deadline:
            time.sleep(poll_interval)

            result = self._client._request(
                "GET",
                f"/v1/orchestrate/{task_id}",
                auth=True,
            )

            if not result.success:
                # Connection errors are transient — keep polling
                if "Connection refused" in (result.error or ""):
                    continue
                elapsed = (time.monotonic() - t0) * 1000
                return HermesOrchestrationResult(
                    task_id=task_id,
                    status="failed",
                    error=result.error,
                    elapsed_ms=elapsed,
                )

            data = result.data or {}
            status = data.get("status", "running")

            if status in ("completed", "failed"):
                elapsed = (time.monotonic() - t0) * 1000
                return HermesOrchestrationResult(
                    task_id=task_id,
                    status=status,
                    result=data.get("result"),
                    plan=data.get("plan"),
                    workers=data.get("workers", []),
                    review=data.get("review"),
                    report=data.get("report") or data.get("output"),
                    error=data.get("error"),
                    elapsed_ms=elapsed,
                )

        # Timeout
        elapsed = (time.monotonic() - t0) * 1000
        return HermesOrchestrationResult(
            task_id=task_id,
            status="timeout",
            error=f"Task timed out after {self.timeout}s",
            elapsed_ms=elapsed,
        )

    # ── Direct chat ───────────────────────────────────────────────────

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
    ) -> HermesResponse:
        """Send a chat completion request through Hermes.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts.
            tools: Optional tool definitions for function calling.
            stream: If True, stream the response (not yet implemented).

        Returns:
            HermesResponse with message, tool_calls, usage.
        """
        t0 = time.monotonic()

        body: Dict[str, Any] = {"messages": messages}
        if tools:
            body["tools"] = tools

        result = self._client._request(
            "POST",
            "/v1/chat/completions",
            auth=True,
            json_body=body,
        )

        elapsed = (time.monotonic() - t0) * 1000

        if not result.success:
            return HermesResponse(
                message=HermesMessage(role="assistant", content=""),
                finish_reason="error",
                elapsed_ms=elapsed,
                raw={"error": result.error},
            )

        data = result.data or {}
        choices = data.get("choices", [{}])
        choice = choices[0] if choices else {}
        msg_data = choice.get("message", {})

        return HermesResponse(
            message=HermesMessage(
                role=msg_data.get("role", "assistant"),
                content=msg_data.get("content", ""),
            ),
            tool_calls=[
                HermesToolCall(
                    id=tc.get("id", ""),
                    name=tc.get("function", {}).get("name", ""),
                    arguments=json.loads(tc.get("function", {}).get("arguments", "{}"))
                    if isinstance(tc.get("function", {}).get("arguments"), str)
                    else tc.get("function", {}).get("arguments", {}),
                )
                for tc in msg_data.get("tool_calls", [])
            ],
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage", {}),
            elapsed_ms=elapsed,
            raw=data,
        )

    # ── Convenience ───────────────────────────────────────────────────

    def science_task(
        self,
        goal: str,
        species: Optional[str] = None,
        region: Optional[str] = None,
        method: Optional[str] = None,
    ) -> HermesOrchestrationResult:
        """Run a scientific task with structured context.

        Args:
            goal: What to accomplish ("SDM", "connectivity", "niche", etc.).
            species: Target species name.
            region: Geographic region.
            method: Algorithm or method ("MaxEnt", "BIOMOD2", etc.).
        """
        parts = [f"Run {goal}"]
        if species:
            parts.append(f"for {species}")
        if region:
            parts.append(f"in {region}")
        if method:
            parts.append(f"using {method}")

        task = " ".join(parts)

        context: Dict[str, Any] = {"workflow": goal}
        if species:
            context["species"] = species
        if region:
            context["region"] = region
        if method:
            context["method"] = method

        return self.orchestrate(task, mode="ecoSeek", context=context)

    def whoami(self) -> Dict[str, Any]:
        """Check Hermes identity through the bridge health endpoint."""
        result = self._client._request("GET", "/health", auth=False)
        return {
            "provider": "hermes",
            "connector": self._client.base_url,
            "healthy": result.success,
            "elapsed_ms": result.elapsed_ms,
            "detail": result.data,
        }

    async def aclose(self):
        """No-op for sync client compatibility."""
        pass
