from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class CriteriaScore(BaseModel):
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized score between 0.0 (unacceptable) and 1.0 (flawless)"
    )
    reasoning: str = Field(description="Detailed rationale explaining the score based on the rubric")


class JudgeEvaluationResult(BaseModel):
    overall_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Weighted composite score across all evaluation criteria"
    )
    is_passed: bool = Field(
        description="True if overall_score >= 0.80 and all critical sub-criteria >= 0.70"
    )
    faithfulness: CriteriaScore = Field(
        description="Measures absence of hallucinations and factual grounding in research context"
    )
    relevance: CriteriaScore = Field(
        description="Measures how directly and accurately the response answers the user's core goal"
    )
    completeness: CriteriaScore = Field(
        description="Measures whether all required components, constraints, and subtasks were fulfilled"
    )
    technical_quality: CriteriaScore = Field(
        description="Measures code correctness, edge-case safety, architectural soundness, or analytical depth"
    )
    format_compliance: CriteriaScore = Field(
        description="Measures adherence to formatting guidelines (markdown, tables, code blocks, schemas)"
    )
    summary_critique: str = Field(
        description="Executive summary of the evaluation, highlighting core strengths and deficiencies"
    )
    improvement_suggestions: List[str] = Field(
        default_factory=list,
        description="Actionable guidance for self-healing improvement"
    )


class BenchmarkTestCase(BaseModel):
    id: str = Field(description="Unique benchmark test case identifier (e.g. code_01, research_02)")
    category: str = Field(description="Domain category: 'coding', 'research', 'reasoning'")
    title: str = Field(description="Short human-readable title")
    prompt: str = Field(description="Input goal/prompt submitted to AgentForge")
    golden_criteria: List[str] = Field(
        description="List of ground-truth criteria the judge will verify against"
    )
    expected_output_type: str = Field(
        default="markdown",
        description="Expected format: 'code', 'report', 'markdown', 'json'"
    )
    difficulty: str = Field(
        default="medium",
        description="'easy', 'medium', 'hard', 'expert'"
    )


class BenchmarkRunResult(BaseModel):
    benchmark_id: str
    category: str
    title: str
    prompt: str
    output: str
    evaluation: JudgeEvaluationResult
    latency_ms: float
    total_tokens: int
    cost_usd: float
    status: str = "completed"


class EvalSummaryReport(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    total_benchmarks: int
    passed_count: int
    failed_count: int
    pass_rate_percentage: float
    average_scores: Dict[str, float]
    total_latency_seconds: float
    total_cost_usd: float
    benchmark_results: List[BenchmarkRunResult]

    def to_markdown(self) -> str:
        status_badge = "🟢 PASSED" if self.pass_rate_percentage >= 80.0 else "🔴 NEEDS IMPROVEMENT"
        
        table_rows = []
        for r in self.benchmark_results:
            icon = "✅" if r.evaluation.is_passed else "❌"
            table_rows.append(
                f"| `{r.benchmark_id}` | {r.title} | {r.category} | {icon} **{r.evaluation.overall_score:.1%}** | "
                f"{r.evaluation.faithfulness.score:.0%} | {r.evaluation.relevance.score:.0%} | "
                f"{r.evaluation.technical_quality.score:.0%} | {r.latency_ms / 1000:.1f}s | ${r.cost_usd:.5f} |"
            )
        rows_str = "\n".join(table_rows)

        return (
            f"# 🧪 LLM-as-Judge Benchmark Evaluation Report\n\n"
            f"**Execution Timestamp:** `{self.timestamp}`  \n"
            f"**Overall Status:** {status_badge}  \n"
            f"**Pass Rate:** **`{self.pass_rate_percentage:.1f}%`** ({self.passed_count}/{self.total_benchmarks} Passed)  \n"
            f"**Total Run Latency:** `{self.total_latency_seconds:.2f}s`  \n"
            f"**Total Evaluation Cost:** `${self.total_cost_usd:.6f} USD`  \n\n"
            f"## 📊 Criteria Score Breakdown\n\n"
            f"| Metric | Average Score |\n"
            f"| :--- | :---: |\n"
            f"| 🎯 **Overall Score** | `{self.average_scores.get('overall', 0.0):.1%}` |\n"
            f"| 🛡️ **Faithfulness / Groundedness** | `{self.average_scores.get('faithfulness', 0.0):.1%}` |\n"
            f"| 🎯 **Answer Relevance** | `{self.average_scores.get('relevance', 0.0):.1%}` |\n"
            f"| 🧩 **Completeness & Depth** | `{self.average_scores.get('completeness', 0.0):.1%}` |\n"
            f"| ⚙️ **Technical & Code Quality** | `{self.average_scores.get('technical_quality', 0.0):.1%}` |\n"
            f"| 📐 **Format Compliance** | `{self.average_scores.get('format_compliance', 0.0):.1%}` |\n\n"
            f"## 📋 Benchmark Case Results\n\n"
            f"| ID | Title | Category | Overall | Faithfulness | Relevance | Tech Quality | Latency | Cost |\n"
            f"| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n"
            f"{rows_str}\n"
        )
