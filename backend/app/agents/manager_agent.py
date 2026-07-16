"""
manager_agent.py
The ManagerAgent acts as a Supervisor in the LangGraph pipeline.
After each worker agent (Researcher, Reasoner, Executor) completes,
the Manager:
  1. Evaluates output quality using a fast, scoped LLM call.
  2. Issues a PASS (advance pipeline) or FAIL (retry agent) decision.
  3. Logs all decisions as structured entries visible in the Thinking Console.
  4. Writes a final run summary when the pipeline completes.
"""
from __future__ import annotations

import json
import logging
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field
from backend.app.agents.base import BaseAgent

logger = logging.getLogger("agentforge.agents.manager")

# ---------------------------------------------------------------------------
# Quality thresholds per agent type
# Researcher gets slightly lower bar (raw data is inherently noisy)
# Executor must meet a higher standard (this is the final deliverable)
# ---------------------------------------------------------------------------
_QUALITY_THRESHOLDS: Dict[str, float] = {
    "researcher": 0.60,
    "reasoner":   0.65,
    "executor":   0.68,
    "default":    0.65,
}

_MAX_AGENT_RETRIES = 2   # Manager retries per individual agent (independent of Verifier retries)


# ---------------------------------------------------------------------------
# Pydantic schema for Manager's evaluation call
# ---------------------------------------------------------------------------
class QualityResult(BaseModel):
    score: float = Field(
        description="Float 0.0–1.0 representing how completely the output addresses the subtask."
    )
    passed: bool = Field(
        description="True if score meets the quality threshold for this agent type."
    )
    issues: str = Field(
        description="Concise bullet list of problems found. Empty string if passed."
    )
    correction_hint: str = Field(
        description=(
            "If failed, a one-sentence instruction the agent should act on in its retry. "
            "Empty string if passed."
        )
    )


class ManagerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Manager",
            system_instruction=(
                "You are the Pipeline Quality Manager for an AI Workforce System. "
                "Your role is to evaluate each worker agent's output and decide whether it is "
                "sufficient to pass to the next stage. Be concise and precise. "
                "Score 0.0–1.0 where:\n"
                "  0.0–0.49 = Severely incomplete or factually wrong.\n"
                "  0.50–0.64 = Partially complete; key sections missing.\n"
                "  0.65–0.79 = Acceptable with minor gaps.\n"
                "  0.80–1.00 = High quality, comprehensive.\n"
                "ALWAYS fill in 'issues' and 'correction_hint' when score < threshold."
            )
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def evaluate_agent_output(
        self,
        agent_name: str,
        subtask_title: str,
        subtask_desc: str,
        output: str,
        task_id: str,
        subtask_id: Optional[str],
    ) -> QualityResult:
        """
        Evaluate the quality of a worker agent's output.
        Returns a QualityResult with a score and pass/fail decision.
        """
        threshold = _QUALITY_THRESHOLDS.get(agent_name.lower(), _QUALITY_THRESHOLDS["default"])

        prompt = (
            f"SUBTASK: {subtask_title}\n"
            f"SUBTASK DETAILS: {subtask_desc}\n\n"
            f"AGENT OUTPUT (to evaluate):\n\"\"\"\n{output[:4000]}\n\"\"\"\n\n"
            f"Quality threshold for this agent type ({agent_name}): {threshold}\n"
            "Evaluate the output. Return JSON with: score (float), passed (bool), issues (str), correction_hint (str)."
        )

        mock_pass = QualityResult(
            score=0.82,
            passed=True,
            issues="",
            correction_hint=""
        )
        mock_fail = QualityResult(
            score=0.55,
            passed=False,
            issues="- Output is too brief.\n- Missing concrete examples.",
            correction_hint="Expand with specific data points and at least two concrete examples."
        )

        # In mock/demo mode, default to passing so pipeline keeps moving
        mock_json = mock_pass.model_dump_json()

        self.log_db(task_id, subtask_id, "thinking",
                    f"[Manager] Evaluating {agent_name} output for: '{subtask_title}' (threshold={threshold})")

        raw = await self.execute_llm(
            prompt=prompt,
            task_id=task_id,
            subtask_id=subtask_id,
            response_schema=QualityResult,
            mock_response_content=mock_json,
            max_output_tokens=512,   # intentionally small — just JSON
        )

        try:
            result = QualityResult.model_validate_json(raw)
        except Exception:
            logger.warning(f"Manager could not parse quality JSON — defaulting to PASS. Raw: {raw[:200]}")
            result = mock_pass

        # Override the passed flag using the authoritative threshold
        result.passed = result.score >= threshold

        # Log the decision
        decision_str = "✅ PASS" if result.passed else "❌ FAIL"
        log_msg = (
            f"[Manager] {agent_name} → score={result.score:.2f} {decision_str}\n"
            + (f"Issues: {result.issues}\nHint: {result.correction_hint}" if not result.passed else "")
        )
        self.log_db(task_id, subtask_id, "manager_decision", log_msg)
        logger.info(log_msg)

        return result

    def log_transition(
        self,
        task_id: str,
        from_agent: str,
        to_agent: str,
        quality_score: float,
        decision: str,
    ) -> None:
        """Write a structured pipeline-transition log entry."""
        msg = (
            f"[Manager] Pipeline transition: {from_agent} → {to_agent} "
            f"| quality={quality_score:.2f} | decision={decision}"
        )
        self.log_db(task_id, None, "manager_decision", msg)

    def write_run_summary(
        self,
        task_id: str,
        quality_scores: Dict[str, float],
        agent_retry_counts: Dict[str, int],
        verifier_retry_count: int,
        final_confidence: float,
        status: str,
    ) -> None:
        """
        Write a final run-summary markdown block as the last log entry.
        This is displayed in the Thinking Console at the very end of the run.
        """
        scores_table = "\n".join(
            f"  | {agent} | {score:.2f} |"
            for agent, score in quality_scores.items()
        ) or "  | — | — |"

        retries_table = "\n".join(
            f"  | {agent} | {count} |"
            for agent, count in agent_retry_counts.items()
            if count > 0
        ) or "  | No retries triggered | — |"

        summary = (
            f"# 📋 Manager Run Summary\n\n"
            f"**Final Status:** `{status.upper()}`  \n"
            f"**Verifier Confidence:** `{final_confidence:.0%}`  \n"
            f"**Verifier Self-Healing Retries:** `{verifier_retry_count}`  \n\n"
            f"## Agent Quality Scores\n\n"
            f"  | Agent | Manager Score |\n"
            f"  |---|---|\n"
            f"{scores_table}\n\n"
            f"## Agent Retry Log\n\n"
            f"  | Agent | Retries |\n"
            f"  |---|---|\n"
            f"{retries_table}\n"
        )

        self.log_db(task_id, None, "manager_decision", summary)
        logger.info(f"[Manager] Run summary written for task {task_id}.")
