from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.agents.base import BaseAgent

class SubtaskPlan(BaseModel):
    title: str = Field(description="Short descriptive title of the subtask")
    description: str = Field(description="Detailed instructions and input for the assigned agent")
    assigned_agent: str = Field(description="Must be one of: researcher, reasoner, executor, memory_agent, verifier")

class PlanResponse(BaseModel):
    reasoning: str = Field(description="Internal thoughts on how to decompose the target goal")
    subtasks: List[SubtaskPlan]

class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Planner",
            system_instruction=(
                "You are the Lead Systems Planner. Your role is to analyze the user's goal, "
                "determine what information must be gathered, analyzed, executed, and verified, "
                "and decompose the goal into a sequence of logical subtasks.\n"
                "Assign each subtask to one of the following specialized agents:\n"
                "- researcher: Searches the web, crawls content, and aggregates documents.\n"
                "- reasoner: Compares data, performs logical deductions, detects inconsistencies.\n"
                "- executor: Creates final code, writes detailed markdown reports, builds spreadsheets.\n"
                "- memory_agent: Saves and retrieves long-term knowledge.\n"
                "IMPORTANT: Keep the plan to a MAXIMUM of 3 subtasks. The verifier agent runs automatically "
                "at the end, so do NOT add a verifier subtask. Each subtask must be high-level and impactful. "
                "Keep subtasks sequential and dependent on each other's outputs."
            )
        )

    async def create_plan(self, prompt: str, task_id: str) -> PlanResponse:
        # Define high-quality mock responses for immediate offline usage
        mock_plan = PlanResponse(
            reasoning="Decomposing the request into search, analysis, and writing steps.",
            subtasks=[
                SubtaskPlan(
                    title="Gather Market Intelligence",
                    description="Search for latest trends, core competitors, market statistics, and pricing models related to: " + prompt,
                    assigned_agent="researcher"
                ),
                SubtaskPlan(
                    title="Perform Comparative Analysis & SWOT",
                    description="Synthesize collected market data, perform SWOT analysis, detect inconsistencies, and compare key features.",
                    assigned_agent="reasoner"
                ),
                SubtaskPlan(
                    title="Compile Strategic Report",
                    description="Synthesize all findings into a polished markdown report with market sizing, competitor matrix, roadmap, and risk register.",
                    assigned_agent="executor"
                ),
            ]
        )
        
        # If prompt is a coding question, adjust the mock
        if any(w in prompt.lower() for w in ["code", "debug", "error", "bug", "program", "function"]):
            mock_plan = PlanResponse(
                reasoning="Decomposing the coding problem into diagnostic, design, and implementation steps.",
                subtasks=[
                    SubtaskPlan(
                        title="Locate Bug and Gather Context",
                        description="Search documentation for error codes, stack traces, and relevant code patterns related to: " + prompt,
                        assigned_agent="researcher"
                    ),
                    SubtaskPlan(
                        title="Diagnose Root Cause",
                        description="Trace variables, evaluate logical flow, and define the exact reason for the failure.",
                        assigned_agent="reasoner"
                    ),
                    SubtaskPlan(
                        title="Implement and Document Fix",
                        description="Write clean, modular, commented code that resolves the issue. Provide usage instructions and SOLID compliance notes.",
                        assigned_agent="executor"
                    ),
                ]
            )

        mock_str = mock_plan.model_dump_json()
        
        result_json = await self.execute_llm(
            prompt=f"Goal: {prompt}",
            task_id=task_id,
            subtask_id=None,
            response_schema=PlanResponse,
            mock_response_content=mock_str
        )
        
        try:
            return PlanResponse.model_validate_json(result_json)
        except Exception:
            return mock_plan
