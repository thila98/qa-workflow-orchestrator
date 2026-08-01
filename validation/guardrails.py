"""
Guardrails
----------
Safety controls that protect against the most common
production failures in multi-agent AI systems.

Problems this solves:
- Runaway loops that burn through API credits overnight
- Agents getting stuck and hanging forever
- Total cost exceeding acceptable limits
- Too many retries on a failing agent

Think of this as the circuit breaker for the whole system.
If something goes wrong, it fails visibly and safely
rather than silently and expensively.
"""

import os
import time
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class WorkflowState:
    """
    Tracks the running state of the entire workflow.
    Passed between agents so each one can check limits.
    """
    # Cost tracking
    total_cost_usd: float = 0.0
    max_cost_usd: float = float(os.getenv("MAX_COST_USD", "0.50"))

    # Retry tracking per agent
    retry_counts: dict = field(default_factory=dict)
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))

    # Timing
    start_time: float = field(default_factory=time.time)
    agent_timeout_seconds: int = int(os.getenv("AGENT_TIMEOUT_SECONDS", "60"))

    # Status tracking
    completed_agents: list = field(default_factory=list)
    failed_agents: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    # Session ID for logging
    session_id: str = ""


class CircuitBreaker:
    """
    Checks safety conditions before each agent runs.
    If any limit is exceeded, raises an exception that
    stops the workflow gracefully.
    """

    def __init__(self, state: WorkflowState):
        self.state = state

    def check_cost_limit(self) -> None:
        """
        Stops the workflow if total API cost exceeds the limit.
        This prevents runaway cost from loops or excessive retries.
        """
        if self.state.total_cost_usd >= self.state.max_cost_usd:
            raise CostLimitExceeded(
                f"Workflow stopped: Total API cost ${self.state.total_cost_usd:.4f} "
                f"reached the limit of ${self.state.max_cost_usd:.2f}. "
                f"You can increase MAX_COST_USD in your .env file."
            )

    def check_retry_limit(self, agent_name: str) -> None:
        """
        Stops an agent from retrying more than the allowed number of times.
        Prevents an agent from looping indefinitely on a failing task.
        """
        retries = self.state.retry_counts.get(agent_name, 0)
        if retries >= self.state.max_retries:
            raise RetryLimitExceeded(
                f"Agent '{agent_name}' has failed {retries} times "
                f"and exceeded the retry limit of {self.state.max_retries}. "
                f"Check the agent logs for the root cause."
            )

    def check_timeout(self, agent_name: str, agent_start_time: float) -> None:
        """
        Stops an agent that has been running too long.
        Prevents the workflow from hanging indefinitely.
        """
        elapsed = time.time() - agent_start_time
        if elapsed > self.state.agent_timeout_seconds:
            raise AgentTimeout(
                f"Agent '{agent_name}' timed out after {elapsed:.1f} seconds. "
                f"The timeout limit is {self.state.agent_timeout_seconds} seconds."
            )

    def check_all(self, agent_name: str, agent_start_time: float) -> None:
        """
        Runs all safety checks at once.
        Call this inside each agent before doing work.
        """
        self.check_cost_limit()
        self.check_retry_limit(agent_name)
        self.check_timeout(agent_name, agent_start_time)

    def record_retry(self, agent_name: str) -> int:
        """
        Records a retry attempt for an agent.
        Returns the current retry count.
        """
        self.state.retry_counts[agent_name] = self.state.retry_counts.get(agent_name, 0) + 1
        return self.state.retry_counts[agent_name]

    def record_cost(self, cost_usd: float) -> None:
        """
        Adds to the running total cost.
        Called after each successful agent API call.
        """
        self.state.total_cost_usd += cost_usd

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimates cost of an API call using Claude Sonnet pricing.
        claude-sonnet-4-6: $3 per 1M input tokens, $15 per 1M output tokens
        """
        input_cost = (input_tokens / 1_000_000) * 3.0
        output_cost = (output_tokens / 1_000_000) * 15.0
        return input_cost + output_cost


# Custom exceptions for clean error handling

class CostLimitExceeded(Exception):
    """Raised when total API cost exceeds the configured limit."""
    pass


class RetryLimitExceeded(Exception):
    """Raised when an agent exceeds its maximum retry count."""
    pass


class AgentTimeout(Exception):
    """Raised when an agent takes too long to respond."""
    pass


class InputValidationError(Exception):
    """Raised when user input fails validation."""
    pass


class OutputValidationError(Exception):
    """Raised when an agent output fails validation."""
    pass


def create_workflow_state(session_id: str = "") -> WorkflowState:
    """
    Creates a fresh workflow state for a new run.
    Call this at the start of every workflow execution.
    """
    import uuid
    return WorkflowState(
        session_id=session_id or str(uuid.uuid4())[:8]
    )
