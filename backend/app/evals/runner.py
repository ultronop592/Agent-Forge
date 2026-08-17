import os
import json
import time
import asyncio
import logging
from typing import List, Optional, Dict, Any

from backend.app.evals.rubrics import (
    BenchmarkTestCase,
    BenchmarkRunResult,
    JudgeEvaluationResult,
    EvalSummaryReport
)
from backend.app.evals.datasets import BENCHMARK_DATASET, get_benchmarks_by_category
from backend.app.evals.evaluator import LLMJudgeEvaluator
from backend.app.agents.executor import ExecutorAgent
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.analyst_agent import AnalystAgent
from backend.app.core.telemetry import agent_traceable, setup_langsmith

logger = logging.getLogger("agentforge.evals.runner")

# Path to store latest evaluation audit report
EVAL_RESULTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "eval_results"
)
LATEST_REPORT_JSON = os.path.join(EVAL_RESULTS_DIR, "latest_eval_report.json")
LATEST_REPORT_MD = os.path.join(EVAL_RESULTS_DIR, "latest_eval_report.md")


class EvalRunner:
    """
    Batch Evaluation Runner for AgentForge.
    Executes benchmark test suites, evaluates deliverables via LLM-as-Judge,
    computes pass-rate metrics, and exports structured reports.
    """

    def __init__(self):
        self.judge = LLMJudgeEvaluator()
        self.planner = PlannerAgent()
        self.analyst = AnalystAgent()
        self.executor = ExecutorAgent()
        os.makedirs(EVAL_RESULTS_DIR, exist_ok=True)

    @agent_traceable(name="AgentForge_Benchmark_Suite_Run", run_type="chain", tags=["agentforge", "evals", "suite"])
    async def run_benchmarks(
        self,
        category: str = "all",
        limit: Optional[int] = None
    ) -> EvalSummaryReport:
        """
        Run evaluations across the selected benchmark dataset.
        """
        setup_langsmith()
        
        benchmarks = get_benchmarks_by_category(category)
        if limit and limit > 0:
            benchmarks = benchmarks[:limit]

        total_cases = len(benchmarks)
        logger.info(f"🧪 Launching LLM-as-Judge Benchmark Evaluation on {total_cases} test cases (category='{category}')...")

        results: List[BenchmarkRunResult] = []
        start_suite_time = time.perf_counter()
        total_suite_cost = 0.0

        for idx, tc in enumerate(benchmarks, start=1):
            logger.info(f"[{idx}/{total_cases}] Evaluating benchmark: '{tc.id}' - {tc.title}...")
            t0 = time.perf_counter()

            # 1. Execute agent generation for the benchmark
            task_id = f"eval_{tc.id}_{int(time.time())}"
            from backend.app.database.connection import SessionLocal
            from backend.app.database.models import Task

            db = SessionLocal()
            try:
                db_task = Task(id=task_id, prompt=tc.prompt, plugin_name="eval_suite", status="running")
                db.add(db_task)
                db.commit()
            except Exception as e:
                logger.warning(f"Could not insert eval task {task_id}: {e}")
            finally:
                db.close()

            try:
                # Step A: Analyst research
                analyst_output = await self.analyst.run_subtask(
                    subtask_title=f"Analyze requirements for {tc.title}",
                    subtask_desc=tc.prompt,
                    task_id=task_id,
                    subtask_id="analyst_sub"
                )

                # Step B: Executor deliverable builder
                generated_output = await self.executor.run_subtask(
                    subtask_title=tc.title,
                    subtask_desc=tc.prompt,
                    context=analyst_output,
                    task_id=task_id,
                    subtask_id="executor_sub"
                )

                # Mark completed
                db = SessionLocal()
                try:
                    t = db.query(Task).filter(Task.id == task_id).first()
                    if t:
                        t.status = "completed"
                        t.final_result = generated_output
                        db.commit()
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Execution failed for benchmark {tc.id}: {e}")
                generated_output = f"Execution error: {str(e)}"

            latency_ms = (time.perf_counter() - t0) * 1000.0

            # 2. Grade output with LLM-as-Judge
            evaluation: JudgeEvaluationResult = await self.judge.evaluate_output(
                prompt=tc.prompt,
                generated_output=generated_output,
                golden_criteria=tc.golden_criteria,
                task_id=task_id
            )

            # Estimate cost & tokens for the benchmark case
            tokens_approx = int(len(tc.prompt.split() + generated_output.split()) * 1.3)
            case_cost = (tokens_approx / 1e6) * 0.30
            total_suite_cost += case_cost

            results.append(BenchmarkRunResult(
                benchmark_id=tc.id,
                category=tc.category,
                title=tc.title,
                prompt=tc.prompt,
                output=generated_output,
                evaluation=evaluation,
                latency_ms=latency_ms,
                total_tokens=tokens_approx,
                cost_usd=round(case_cost, 6),
                status="completed"
            ))

        total_duration = time.perf_counter() - start_suite_time
        passed_count = sum(1 for r in results if r.evaluation.is_passed)
        failed_count = total_cases - passed_count
        pass_rate = round((passed_count / total_cases * 100.0) if total_cases > 0 else 0.0, 2)

        # Compute average score across each criterion
        avg_scores = {
            "overall": round(sum(r.evaluation.overall_score for r in results) / total_cases, 3) if total_cases else 0.0,
            "faithfulness": round(sum(r.evaluation.faithfulness.score for r in results) / total_cases, 3) if total_cases else 0.0,
            "relevance": round(sum(r.evaluation.relevance.score for r in results) / total_cases, 3) if total_cases else 0.0,
            "completeness": round(sum(r.evaluation.completeness.score for r in results) / total_cases, 3) if total_cases else 0.0,
            "technical_quality": round(sum(r.evaluation.technical_quality.score for r in results) / total_cases, 3) if total_cases else 0.0,
            "format_compliance": round(sum(r.evaluation.format_compliance.score for r in results) / total_cases, 3) if total_cases else 0.0,
        }

        report = EvalSummaryReport(
            total_benchmarks=total_cases,
            passed_count=passed_count,
            failed_count=failed_count,
            pass_rate_percentage=pass_rate,
            average_scores=avg_scores,
            total_latency_seconds=round(total_duration, 2),
            total_cost_usd=round(total_suite_cost, 6),
            benchmark_results=results
        )

        # Save reports
        try:
            with open(LATEST_REPORT_JSON, "w", encoding="utf-8") as f:
                f.write(report.model_dump_json(indent=2))

            with open(LATEST_REPORT_MD, "w", encoding="utf-8") as f:
                f.write(report.to_markdown())
            logger.info(f"📊 Evaluation reports saved to '{LATEST_REPORT_MD}' and '{LATEST_REPORT_JSON}'")
        except Exception as e:
            logger.error(f"Failed to write evaluation report file: {e}")

        logger.info(f"✅ Evaluation Complete! Pass Rate: {pass_rate:.1f}% ({passed_count}/{total_cases} passed in {total_duration:.1f}s)")
        return report


def get_latest_report() -> Optional[EvalSummaryReport]:
    """Load latest evaluation report from disk if present."""
    if os.path.exists(LATEST_REPORT_JSON):
        try:
            with open(LATEST_REPORT_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                return EvalSummaryReport.model_validate(data)
        except Exception as e:
            logger.error(f"Failed to load latest eval report: {e}")
    return None


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    runner = EvalRunner()
    category = sys.argv[1] if len(sys.argv) > 1 else "all"
    report = asyncio.run(runner.run_benchmarks(category=category))
    print("\n" + report.to_markdown())
