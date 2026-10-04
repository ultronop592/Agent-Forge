from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.core.agent_config import agent_config_registry

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentConfigUpdate(BaseModel):
    model: Optional[str] = Field(default=None, description="Model identifier e.g. gemini-2.5-flash")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Sampling temperature 0.0 - 1.0")
    token_budget: Optional[int] = Field(default=None, ge=250, le=32000, description="Max output tokens budget ceiling")
    custom_instruction: Optional[str] = Field(default=None, description="Custom steering prompt addendum for this agent")


class BulkAgentConfigUpdate(BaseModel):
    configs: Dict[str, Dict[str, Any]]


@router.get("")
def list_agents() -> List[Dict[str, Any]]:
    agents = [
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
    # Attach current active configuration to each agent card
    for a in agents:
        cfg = agent_config_registry.get_agent_config(a["name"])
        a["config"] = cfg
    return agents


@router.get("/config")
def get_all_agent_configs() -> Dict[str, Any]:
    """Retrieve active configurations for all agents and global defaults."""
    return agent_config_registry.get_all_configs()


@router.get("/config/{agent_name}")
def get_single_agent_config(agent_name: str) -> Dict[str, Any]:
    """Retrieve active configuration for a specific agent role."""
    return agent_config_registry.get_agent_config(agent_name)


@router.put("/config/{agent_name}")
def update_single_agent_config(agent_name: str, payload: AgentConfigUpdate) -> Dict[str, Any]:
    """Update configuration (model, temperature, token_budget, custom_instruction) for an agent."""
    updates = payload.model_dump(exclude_unset=True)
    updated = agent_config_registry.update_agent_config(agent_name, updates)
    return {"message": f"Configuration updated for {agent_name}", "agent": agent_name, "config": updated}


@router.put("/config")
def update_bulk_agent_configs(payload: BulkAgentConfigUpdate) -> Dict[str, Any]:
    """Bulk update configurations across multiple agents."""
    return agent_config_registry.update_all_configs(payload.configs)


@router.post("/config/reset")
def reset_agent_configs() -> Dict[str, Any]:
    """Reset all agent configurations to platform factory defaults."""
    agent_config_registry.reset()
    return {"message": "Agent configurations successfully reset to defaults", "data": agent_config_registry.get_all_configs()}

