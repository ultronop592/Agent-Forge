from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter(prefix="/agents", tags=["agents"])

@router.get("")
def list_agents() -> List[Dict[str, Any]]:
    return [
        {
            "name": "Planner",
            "role": "Lead Architect",
            "status": "idle",
            "description": "Analyzes user request, splits it into structured subtasks, and schedules agent execution sequences.",
            "tools": ["State Decomposer"]
        },
        {
            "name": "Researcher",
            "role": "Data Collector",
            "status": "idle",
            "description": "Searches the web via Tavily, crawls target URLs, and compiles raw references and citation reports.",
            "tools": ["Web Search (Tavily)", "Document Fetcher"]
        },
        {
            "name": "Reasoner",
            "role": "Critical Analyst",
            "status": "idle",
            "description": "Performs logical analysis, evaluates conflicting statistics, identifies structural gaps, and lists entry constraints.",
            "tools": ["SWOT Analyser", "Consistency Evaluator"]
        },
        {
            "name": "Executor",
            "role": "Developer & Author",
            "status": "idle",
            "description": "Aggregates findings and drafts the final code or report according to design blueprints.",
            "tools": ["Code Compiler", "Markdown Report Writer"]
        },
        {
            "name": "Verifier",
            "role": "QA & Fact-Checker",
            "status": "idle",
            "description": "Inspects executor deliverables against original guidelines, runs lint validation, and scores factual certainty.",
            "tools": ["Hallucination Detector", "Confidence Scorer"]
        },
        {
            "name": "MemoryAgent",
            "role": "Librarian",
            "status": "idle",
            "description": "Manages recall of past task results and saves new insights to the long-term semantic memory storage.",
            "tools": ["Semantic Query", "Memory Store"]
        }
    ]
