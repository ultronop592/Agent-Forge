from typing import Dict, Any, List
from backend.app.plugins.base_plugin import BaseWorkflowPlugin


class GeneralAnalysisPlugin(BaseWorkflowPlugin):
    @property
    def name(self) -> str:
        return "General Deep-Dive Analysis"

    @property
    def plugin_id(self) -> str:
        return "general_analysis"

    @property
    def description(self) -> str:
        return (
            "Executes comprehensive cross-functional analysis, multi-perspective strategic evaluations, "
            "empirical data synthesis, and actionable decision frameworks."
        )

    def get_custom_system_instruction(self, agent_name: str) -> str:
        if agent_name == "Planner":
            return (
                "You are a Lead Strategic Planning Director. Deconstruct broad analysis objectives into "
                "structured investigation, hypothesis testing, comparative evaluation, and executive synthesis subtasks."
            )
        elif agent_name == "Researcher":
            return (
                "You are a Cross-Disciplinary Research Specialist. Search for empirical studies, primary data sources, "
                "industry benchmarks, historical precedents, and statistical evidence."
            )
        elif agent_name == "Reasoner":
            return (
                "You are a Critical Thinking & Analytical Logic Specialist. Stress-test assumptions, identify cognitive biases, "
                "model second-order effects, perform qualitative and quantitative tradeoffs, and evaluate decision trees."
            )
        elif agent_name == "Executor":
            return (
                "You are an Executive Communications Lead. Synthesize complex analytical findings into a clear, highly structured "
                "briefing with executive summaries, comparative tables, decision matrices, and risk mitigations."
            )
        elif agent_name == "Verifier":
            return (
                "You are an Academic Peer Reviewer and Facts Verifier. Scrutinize analytical reasoning for logical fallacies, "
                "verify calculations, confirm source reliability, and ensure rigorous objectivity."
            )
        return ""

    def get_default_subtasks(self, prompt: str) -> List[Dict[str, Any]]:
        return [
            {
                "title": "Gather Empirical Evidence & Source Material",
                "description": f"Search academic sources, industry benchmarks, primary statistics, and historical precedents related to: {prompt}",
                "assigned_agent": "researcher",
                "order_index": 0
            },
            {
                "title": "Multi-Perspective Critical Evaluation & Tradeoff Modeling",
                "description": (
                    "Analyze core hypotheses, identify second-order effects, map out contrasting viewpoints, "
                    "and conduct structured tradeoff modeling on the gathered evidence."
                ),
                "assigned_agent": "reasoner",
                "order_index": 1
            },
            {
                "title": "Synthesize Comprehensive Decision Analysis Report",
                "description": (
                    "Compile analytical findings into a structured report featuring an executive summary, "
                    "comparative matrix, scenario analyses, actionable recommendations, and risk assessment."
                ),
                "assigned_agent": "executor",
                "order_index": 2
            }
        ]
