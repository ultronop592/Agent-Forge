from typing import Dict, Any, List
from backend.app.plugins.base_plugin import BaseWorkflowPlugin

class StartupResearchPlugin(BaseWorkflowPlugin):
    @property
    def name(self) -> str:
        return "Startup Market Research"

    @property
    def plugin_id(self) -> str:
        return "startup_research"

    @property
    def description(self) -> str:
        return "Conducts comprehensive market sizing, competitor audits, business model designs, and strategic risks evaluations."

    def get_custom_system_instruction(self, agent_name: str) -> str:
        if agent_name == "Planner":
            return "You are a Venture Capital Principal Planner. Break market research requests into clear intelligence subtasks."
        elif agent_name == "Researcher":
            return "You are a professional Business Intelligence Analyst. Extract market stats, pricing structures, and news."
        elif agent_name == "Reasoner":
            return "You are a Strategy Advisor. Identify market entry barriers, evaluate competitor gaps, and run SWOT analyses."
        elif agent_name == "Executor":
            return "You are a Business Writer. Craft polished executive pitches, investment theses, and market reports."
        elif agent_name == "Verifier":
            return "You are a Fact-Checking Specialist. Double check market sizing figures, currency rates, and dates."
        return ""

    def get_default_subtasks(self, prompt: str) -> List[Dict[str, Any]]:
        return [
            {
                "title": "Research Competitors, Pricing & Market Data",
                "description": f"Search for top companies in this niche, their pricing models, feature lists, and market share: {prompt}",
                "assigned_agent": "researcher",
                "order_index": 0
            },
            {
                "title": "Evaluate Market Gaps and SWOT",
                "description": "Analyze competitor weak points. Outline strengths, weaknesses, opportunities, and entry risks. Cross-reference data points.",
                "assigned_agent": "reasoner",
                "order_index": 1
            },
            {
                "title": "Draft Strategic Business Report",
                "description": "Combine SWOT and stats into a formatted report with market sizing table, competitive matrix, execution roadmap, and risk register.",
                "assigned_agent": "executor",
                "order_index": 2
            }
        ]
