"""
manager_agent.py
─────────────────────────────────────────────────────────────────────────────
The ManagerAgent is the orchestration coordinator of the AI Workforce System.

It does NOT make LLM calls (keeping the pipeline at 5 total API calls).
Instead it acts as the authoritative supervisor that:

  1. Announces when each worker agent starts execution.
  2. Logs every pipeline transition (agent_A → agent_B) with timing context.
  3. Flags skipped or retried agents clearly in the Thinking Console.
  4. Writes a structured Markdown run-summary at the very end of every task.

All log entries appear in the frontend Thinking Console under the
"Manager Decisions" channel (amber highlight).
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from backend.app.agents.base import BaseAgent

logger = logging.getLogger("agentforge.agents.manager")


class ManagerAgent(BaseAgent):
    """Lightweight orchestration coordinator — no LLM calls."""

    def __init__(self) -> None:
        super().__init__(
            name="Manager",
            system_instruction=(
                "You are the Pipeline Coordinator of the AgentForge Workforce System. "
                "Your role is to supervise, route, and log the execution of all worker agents."
            ),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Transition & lifecycle logging
    # ─────────────────────────────────────────────────────────────────────────

    def announce_start(
        self,
        task_id: str,
        agent_name: str,
        subtask_title: str,
        subtask_id: Optional[str] = None,
    ) -> None:
        """Log that an agent is about to begin a subtask."""
        msg = (
            f"🚀 [Manager] Dispatching **{agent_name}** agent\n"
            f"   └─ Subtask: \"{subtask_title}\""
        )
        self.log_db(task_id, subtask_id, "manager_decision", msg)
        logger.info(msg)

    def announce_complete(
        self,
        task_id: str,
        agent_name: str,
        subtask_title: str,
        subtask_id: Optional[str] = None,
    ) -> None:
        """Log that an agent finished successfully."""
        msg = (
            f"✅ [Manager] **{agent_name}** completed\n"
            f"   └─ Subtask: \"{subtask_title}\""
        )
        self.log_db(task_id, subtask_id, "manager_decision", msg)
        logger.info(msg)

    def announce_parallel_dispatch(
        self,
        task_id: str,
        agent_names: list[str],
    ) -> None:
        """Log that multiple agents are being dispatched in parallel."""
        agents_str = " & ".join(f"**{name}**" for name in agent_names)
        msg = (
            f"⚡ [Manager] Parallel Stage Activated: Launching {agents_str} concurrently\n"
            f"   └─ Subtasks executing in parallel with asyncio.gather()"
        )
        self.log_db(task_id, None, "manager_decision", msg)
        logger.info(msg)

    def announce_parallel_complete(
        self,
        task_id: str,
        agent_names: list[str],
    ) -> None:
        """Log that all parallel agents finished execution."""
        agents_str = " & ".join(f"**{name}**" for name in agent_names)
        msg = (
            f"✅ [Manager] Parallel Stage Complete: {agents_str} finished\n"
            f"   └─ Aggregating intelligence outputs for Executor"
        )
        self.log_db(task_id, None, "manager_decision", msg)
        logger.info(msg)

    def log_transition(
        self,
        task_id: str,
        from_agent: str,
        to_agent: str,
        reason: str = "output accepted",
    ) -> None:
        """Log a pipeline transition between two agents."""
        msg = (
            f"🔀 [Manager] Pipeline: **{from_agent}** → **{to_agent}**\n"
            f"   └─ Reason: {reason}"
        )
        self.log_db(task_id, None, "manager_decision", msg)
        logger.info(msg)

    def log_plan_received(
        self,
        task_id: str,
        subtask_count: int,
        subtask_titles: list[str],
    ) -> None:
        """Log the plan produced by the Planner so it's visible in the console."""
        bullet_list = "\n".join(
            f"   {i + 1}. {title}" for i, title in enumerate(subtask_titles)
        )
        msg = (
            f"📋 [Manager] Plan received from Planner — {subtask_count} subtask(s) queued:\n"
            f"{bullet_list}"
        )
        self.log_db(task_id, None, "manager_decision", msg)
        logger.info(msg)

    def log_verifier_retry(
        self,
        task_id: str,
        attempt: int,
        max_retries: int,
        feedback: str,
    ) -> None:
        """Log a self-healing retry decision made by the Verifier."""
        msg = (
            f"🔁 [Manager] Self-healing triggered (Attempt {attempt}/{max_retries})\n"
            f"   └─ Verifier feedback: {feedback}\n"
            f"   └─ Routing back to Executor for correction."
        )
        self.log_db(task_id, None, "manager_decision", msg)
        logger.warning(msg)

    # ─────────────────────────────────────────────────────────────────────────
    # Final run summary
    # ─────────────────────────────────────────────────────────────────────────

    def write_run_summary(
        self,
        task_id: str,
        verifier_retry_count: int,
        final_confidence: float,
        status: str,
        agent_sequence: list[str],
    ) -> None:
        """
        Write a structured Markdown run-summary as the final log entry.
        Displayed prominently in the Thinking Console.
        """
        from backend.app.database.connection import SessionLocal
        from backend.app.database.models import AgentLog
        from backend.app.core.config import settings
        from backend.app.core.telemetry import is_langsmith_enabled

        status_emoji = "✅" if status == "completed" else "❌"
        pipeline_str = " → ".join(agent_sequence) if agent_sequence else "N/A"

        # Calculate run metrics from database
        db = SessionLocal()
        total_tokens = 0
        prompt_tokens = 0
        completion_tokens = 0
        total_latency_ms = 0.0
        total_cost = 0.0

        try:
            logs = db.query(AgentLog).filter(AgentLog.task_id == task_id).all()
            for log in logs:
                if log.prompt_tokens:
                    prompt_tokens += log.prompt_tokens
                if log.completion_tokens:
                    completion_tokens += log.completion_tokens
                if log.total_tokens:
                    total_tokens += log.total_tokens
                if log.latency_ms:
                    total_latency_ms += log.latency_ms
                if log.cost_usd:
                    total_cost += log.cost_usd
        finally:
            db.close()

        langsmith_status = (
            f"🟢 Active (`{settings.langsmith_project}`)"
            if is_langsmith_enabled()
            else "📊 Local Telemetry (Zero network overhead)"
        )

        summary = (
            f"# 📋 Manager Run Summary\n\n"
            f"**Final Status:** {status_emoji} `{status.upper()}`  \n"
            f"**QA Confidence Score:** `{final_confidence:.0%}`  \n"
            f"**Self-Healing Retries:** `{verifier_retry_count}`  \n"
            f"**LangSmith Tracing:** {langsmith_status}  \n\n"
            f"## Pipeline Execution Order\n\n"
            f"`{pipeline_str}`\n\n"
            f"## Observability & Performance Metrics\n\n"
            f"| Metric | Value |\n"
            f"|--------|-------|\n"
            f"| ⏱️ Total Pipeline Latency | **{total_latency_ms / 1000.0:.2f}s** ({total_latency_ms:.0f}ms) |\n"
            f"| 🪙 Total Token Consumption | **{total_tokens:,}** (Input: {prompt_tokens:,}, Output: {completion_tokens:,}) |\n"
            f"| 💵 Estimated LLM Run Cost | **${total_cost:.6f} USD** |\n"
            f"| 👑 Manager Overhead | 0 LLM calls (Zero token cost) |\n"
            f"| 🧠 Embedding Vector Reuse | ✅ Cached query vector |\n"
            f"| 🔍 Analyst Mode | ✅ Unified Search + SWOT Reasoning |\n"
        )

        self.log_db(task_id, None, "manager_decision", summary)
        logger.info(f"[Manager] Run summary written for task {task_id}.")
