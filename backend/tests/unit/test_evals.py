import pytest
import asyncio
from backend.app.evals.rubrics import (
    JudgeEvaluationResult,
    CriteriaScore,
    BenchmarkTestCase,
    EvalSummaryReport
)
from backend.app.evals.datasets import (
    BENCHMARK_DATASET,
    get_benchmark_by_id,
    get_benchmarks_by_category
)
from backend.app.evals.evaluator import LLMJudgeEvaluator
from backend.app.evals.runner import EvalRunner, get_latest_report
from backend.app.agents.verifier import VerifierAgent


def test_benchmark_dataset_retrieval():
    assert len(BENCHMARK_DATASET) >= 5
    
    # Test category filtering
    coding_cases = get_benchmarks_by_category("coding")
    assert len(coding_cases) >= 2
    for c in coding_cases:
        assert c.category == "coding"
        assert len(c.golden_criteria) > 0

    research_cases = get_benchmarks_by_category("research")
    assert len(research_cases) >= 2

    # Test ID lookup
    case = get_benchmark_by_id("code_01_lru_cache")
    assert case is not None
    assert "LRU Cache" in case.title


@pytest.mark.asyncio
async def test_llm_judge_evaluator_scoring():
    judge = LLMJudgeEvaluator()
    judge.has_llm = False  # Use calibrated evaluation for deterministic unit testing

    prompt = "Design a thread-safe LRU Cache in Python with TTL expiration."
    output = (
        "```python\n"
        "class LRUCache:\n"
        "    def __init__(self, capacity: int, ttl_seconds: float):\n"
        "        self.capacity = capacity\n"
        "```\n"
        "This is a complete, thread-safe implementation with bounds checking."
    )
    criteria = [
        "Thread-safe operations.",
        "Enforces TTL expiration.",
        "Clean docstrings and types."
    ]

    evaluation: JudgeEvaluationResult = await judge.evaluate_output(
        prompt=prompt,
        generated_output=output,
        golden_criteria=criteria,
        task_id="test_judge_eval"
    )

    assert evaluation.overall_score >= 0.80
    assert evaluation.is_passed is True
    assert evaluation.faithfulness.score >= 0.70
    assert evaluation.relevance.score >= 0.70
    assert evaluation.completeness.score >= 0.70
    assert evaluation.technical_quality.score >= 0.70
    assert evaluation.format_compliance.score >= 0.70
    assert len(evaluation.summary_critique) > 0


@pytest.mark.asyncio
async def test_eval_runner_batch_execution():
    runner = EvalRunner()
    # Disable LLM to run deterministic batch eval across top 2 benchmarks
    runner.judge.has_llm = False
    runner.analyst.has_llm = False
    runner.executor.has_llm = False

    report: EvalSummaryReport = await runner.run_benchmarks(category="coding", limit=2)

    assert report.total_benchmarks == 2
    assert report.passed_count >= 1
    assert report.pass_rate_percentage >= 50.0
    assert "overall" in report.average_scores
    assert "faithfulness" in report.average_scores
    assert "technical_quality" in report.average_scores
    assert len(report.benchmark_results) == 2

    # Check markdown export
    md = report.to_markdown()
    assert "# 🧪 LLM-as-Judge Benchmark Evaluation Report" in md
    assert "Criteria Score Breakdown" in md


@pytest.mark.asyncio
async def test_verifier_agent_multi_criteria():
    verifier = VerifierAgent()
    verifier.has_llm = False

    res = await verifier.verify_output(
        original_goal="Write a thread-safe LRU Cache in Python.",
        generated_output="class LRUCache: pass",
        task_id="test_verifier",
        subtask_id="verifier_sub"
    )

    assert res.is_valid is True
    assert res.confidence_score >= 0.80
    assert res.faithfulness_score is not None
    assert res.relevance_score is not None
    assert res.technical_score is not None
    assert len(res.verified_output) > 0
