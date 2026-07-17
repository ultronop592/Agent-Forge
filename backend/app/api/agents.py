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
            "description": "Analyzes user requests, splits goals into structured subtask chains, and manages workflows.",
            "tools": ["Plan Decomposer"]
        },
        {
            "name": "Manager",
            "role": "Orchestration Supervisor",
            "status": "idle",
            "description": "Supervises multi-agent routing, coordinates parallel stages, logs pipeline transitions, and writes final run summaries.",
            "tools": ["State Coordinator", "Pipeline Router"]
        },
        {
            "name": "Analyst",
            "role": "Research & SWOT Analyst",
            "status": "idle",
            "description": "Performs web queries via Tavily, analyzes tradeoffs, and performs SWOT synthesis in a single unified step.",
            "tools": ["Web Search (Tavily)", "SWOT Compiler"]
        },
        {
            "name": "Executor",
            "role": "Deliverables Builder",
            "status": "idle",
            "description": "Aggregates prior agent context and drafts polished code, reports, or data files.",
            "tools": ["Code Generator", "Report Writer"]
        },
        {
            "name": "Verifier",
            "role": "QA Fact-Checker",
            "status": "idle",
            "description": "Cross-checks executor deliverables against requirements, scoring confidence and triggering self-healing loopbacks.",
            "tools": ["Hallucination Detector", "Verification Evaluator"]
        },
        {
            "name": "MemoryAgent",
            "role": "Institutional Librarian",
            "status": "idle",
            "description": "Manages recall of context before task runs and saves verified lessons via vector embeddings.",
            "tools": ["Semantic Similarity", "Vector Storage"]
        }
    ]
