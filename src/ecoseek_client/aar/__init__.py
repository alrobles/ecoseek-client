"""AAR / ReAct loop — observe → reason → act → evaluate → update.

Minimal, testable scientific agent loop that routes reasoning through
HermesProvider and acts via AgenticPlug task dispatch.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..providers.hermes import HermesMessage, HermesProvider


@dataclass
class Observation:
    """An observation from the environment."""

    source: str  # "agenticplug", "hpc", "hermes", "filesystem"
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Action:
    """An action to execute."""

    tool: str  # tool name: "agenticplug.task", "hermes.chat", "hpc.submit"
    params: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass
class ActionResult:
    """Result of executing an action."""

    action: Action
    success: bool
    data: Any = None
    error: Optional[str] = None
    elapsed_ms: float = 0.0


@dataclass
class AARCycle:
    """One complete AAR cycle."""

    cycle_id: int
    observation: Observation
    reasoning: str  # Hermes' reasoning about what to do
    action: Action
    result: ActionResult
    evaluation: str  # Hermes' evaluation of the result
    updated_context: Dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0


@dataclass
class AARResult:
    """Final result of an AAR session."""

    cycles: List[AARCycle] = field(default_factory=list)
    final_observation: Optional[Observation] = None
    summary: str = ""
    success: bool = False
    total_elapsed_ms: float = 0.0


class AARLoop:
    """Observe → Reason → Act → Evaluate → Update loop.

    Powered by Hermes for reasoning and evaluation, AgenticPlug for actions.

    Usage:
        loop = AARLoop(provider=hermes_provider)
        result = await loop.run("Check HPC cluster status and report")
    """

    MAX_CYCLES: int = 5

    def __init__(self, provider: HermesProvider, max_cycles: int = 5):
        self.provider = provider
        self.max_cycles = max_cycles
        self._context: Dict[str, Any] = {}
        self._cycles: List[AARCycle] = []

    def run(
        self,
        goal: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> AARResult:
        """Run the AAR loop until goal is achieved or max cycles reached.

        Args:
            goal: What to accomplish.
            initial_context: Initial context (files, constraints, etc.).

        Returns:
            AARResult with all cycles, final state, and summary.
        """
        t0 = time.monotonic()
        self._context = dict(initial_context or {})
        self._cycles = []

        for cycle_id in range(1, self.max_cycles + 1):
            ct0 = time.monotonic()

            # 1. Observe — gather state from AgenticPlug
            observation = self._observe()

            # 2. Reason — ask Hermes what to do
            reasoning, action = self._reason(goal, observation, cycle_id)

            # 3. Act — execute the action
            result = self._act(action)

            # 4. Evaluate — did it work? what next?
            evaluation, done = self._evaluate(goal, observation, action, result)

            # 5. Update — store context for next cycle
            self._update(result, evaluation)

            elapsed = (time.monotonic() - ct0) * 1000
            cycle = AARCycle(
                cycle_id=cycle_id,
                observation=observation,
                reasoning=reasoning,
                action=action,
                result=result,
                evaluation=evaluation,
                updated_context=dict(self._context),
                elapsed_ms=elapsed,
            )
            self._cycles.append(cycle)

            if done:
                total_elapsed = (time.monotonic() - t0) * 1000
                return AARResult(
                    cycles=self._cycles,
                    final_observation=self._observe(),
                    summary=evaluation,
                    success=True,
                    total_elapsed_ms=total_elapsed,
                )

        total_elapsed = (time.monotonic() - t0) * 1000
        return AARResult(
            cycles=self._cycles,
            final_observation=self._observe(),
            summary=f"Reached max cycles ({self.MAX_CYCLES}) without completing goal",
            success=False,
            total_elapsed_ms=total_elapsed,
        )

    def _observe(self) -> Observation:
        """Observe the current state from AgenticPlug."""
        # Get connector health
        health = self.provider.client.health()
        health_data = {
            "healthy": health.success,
            "elapsed_ms": health.elapsed_ms,
            "connector_url": self.provider.client.base_url,
        }
        if health.data:
            health_data.update(health.data)

        # If auth available, get clusters
        clusters_data: Dict[str, Any] = {}
        if self.provider.client.has_auth:
            clusters = self.provider.client.clusters()
            if clusters.success and clusters.data:
                clusters_data = clusters.data

        return Observation(
            source="agenticplug",
            data={
                "health": health_data,
                "clusters": clusters_data,
                "auth_configured": self.provider.client.has_auth,
            },
        )

    def _reason(
        self,
        goal: str,
        observation: Observation,
        cycle_id: int,
    ) -> tuple[str, Action]:
        """Ask Hermes what to do given the goal and current observation."""
        # Build reasoning prompt
        messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "You are an AAR (After Action Review) reasoning engine for EcoSeek. "
                    "Given a goal and current observation, decide what action to take. "
                    "Reply with: REASONING: <why> then ACTION: <tool_name> with <params>. "
                    "Available tools: agenticplug.task (run named tasks like remote.health, "
                    "hpc.status, hpc.queue), hermes.orchestrate (full agent orchestration), "
                    "done (goal achieved, no more actions)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Goal: {goal}\n"
                    f"Cycle: {cycle_id}/{self.MAX_CYCLES}\n"
                    f"Observation: {observation.data}\n"
                    f"Previous context: {self._context}\n"
                    "\nWhat action should I take?"
                ),
            },
        ]

        response = self.provider.chat(messages)

        # Parse Hermes' response for ACTION
        content = response.message.content or ""

        # Extract action from the response
        action = self._parse_action(content)

        return content, action

    def _parse_action(self, reasoning: str) -> Action:
        """Parse an action from Hermes' reasoning text."""
        action = Action(tool="done", params={}, reason=reasoning[:200])

        if "agenticplug.task" in reasoning.lower():
            # Extract task name
            for task_name in ("remote.health", "hpc.status", "hpc.queue", "hpc.submit"):
                if task_name in reasoning:
                    action = Action(
                        tool="agenticplug.task",
                        params={"task_name": task_name},
                        reason=reasoning[:200],
                    )
                    break
            else:
                action = Action(
                    tool="agenticplug.task",
                    params={"task_name": "remote.health"},
                    reason=reasoning[:200],
                )

        elif "hermes.orchestrate" in reasoning.lower():
            action = Action(
                tool="hermes.orchestrate",
                params={"task": reasoning},
                reason=reasoning[:200],
            )

        return action

    def _act(self, action: Action) -> ActionResult:
        """Execute the action."""
        t0 = time.monotonic()

        try:
            if action.tool == "agenticplug.task":
                task_name = action.params.get("task_name", "remote.health")
                result = self.provider.client.task(task_name)
                elapsed = (time.monotonic() - t0) * 1000
                return ActionResult(
                    action=action,
                    success=result.success,
                    data=result.data,
                    error=result.error,
                    elapsed_ms=elapsed,
                )

            elif action.tool == "hermes.orchestrate":
                task = action.params.get("task", "")
                result = self.provider.orchestrate(task, wait=True)
                elapsed = (time.monotonic() - t0) * 1000
                return ActionResult(
                    action=action,
                    success=result.status == "completed",
                    data={
                        "task_id": result.task_id,
                        "status": result.status,
                        "report": result.report,
                    },
                    error=result.error,
                    elapsed_ms=elapsed,
                )

            elif action.tool == "done":
                elapsed = (time.monotonic() - t0) * 1000
                return ActionResult(
                    action=action,
                    success=True,
                    data={"status": "done"},
                    elapsed_ms=elapsed,
                )

            else:
                elapsed = (time.monotonic() - t0) * 1000
                return ActionResult(
                    action=action,
                    success=False,
                    error=f"Unknown tool: {action.tool}",
                    elapsed_ms=elapsed,
                )

        except Exception as exc:
            elapsed = (time.monotonic() - t0) * 1000
            return ActionResult(
                action=action,
                success=False,
                error=str(exc),
                elapsed_ms=elapsed,
            )

    def _evaluate(
        self,
        goal: str,
        observation: Observation,
        action: Action,
        result: ActionResult,
    ) -> tuple[str, bool]:
        """Ask Hermes to evaluate the result and decide if goal is achieved."""
        messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "Evaluate whether the action achieved the goal. "
                    "Reply with EVALUATION: <assessment> and DONE: true or false."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Goal: {goal}\n"
                    f"Action: {action.tool} with {action.params}\n"
                    f"Result: success={result.success}, data={result.data}, error={result.error}\n"
                    "\nIs the goal achieved? Reply with DONE: true/false and EVALUATION."
                ),
            },
        ]

        response = self.provider.chat(messages)
        content = response.message.content or ""

        done = "DONE: true" in content.lower() or "done: true" in content.lower()

        return content, done

    def _update(self, result: ActionResult, evaluation: str):
        """Update the internal context based on the cycle result."""
        self._context["last_action_result"] = {
            "success": result.success,
            "data": result.data,
            "error": result.error,
        }
        self._context["last_evaluation"] = evaluation
        self._context["cycles_completed"] = len(self._cycles)
