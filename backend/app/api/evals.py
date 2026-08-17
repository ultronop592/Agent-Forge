import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Query, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.app.evals.datasets import BENCHMARK_DATASET, get_benchmarks_by_category
from backend.app.evals.runner import EvalRunner, get_latest_report
from backend.app.evals.rubrics import EvalSummaryReport

logger = logging.getLogger("agentforge.api.evals")

router = APIRouter(prefix="/evals", tags=["evaluations"])


class RunEvalRequest(BaseModel):
    category: str = "all"
    limit: Optional[int] = None


@router.get("/benchmarks")
def list_benchmarks(category: Optional[str] = Query(default="all")):
    """List available evaluation benchmark datasets."""
    benchmarks = get_benchmarks_by_category(category or "all")
    return {
        "total_count": len(benchmarks),
        "category": category,
        "benchmarks": [b.model_dump() for b in benchmarks]
    }


@router.get("/latest")
def get_latest_evaluation():
    """Retrieve the most recent benchmark evaluation report."""
    report = get_latest_report()
    if not report:
        raise HTTPException(
            status_code=404,
            detail="No evaluation reports found. Run /api/evals/run first to generate a report."
        )
    return report.model_dump()


@router.post("/run")
async def run_evaluation(request: RunEvalRequest):
    """
    Execute the LLM-as-Judge evaluation pipeline across benchmark datasets.
    Computes pass-rate metrics, criteria score breakdowns, and generates audit reports.
    """
    try:
        runner = EvalRunner()
        report: EvalSummaryReport = await runner.run_benchmarks(
            category=request.category,
            limit=request.limit
        )
        return {
            "status": "success",
            "message": f"Evaluated {report.total_benchmarks} benchmarks with {report.pass_rate_percentage:.1f}% pass rate.",
            "report": report.model_dump()
        }
    except Exception as e:
        logger.error(f"Error during benchmark evaluation run: {e}")
        raise HTTPException(status_code=500, detail=str(e))
