from typing import Dict, Any, List
from backend.app.plugins.base_plugin import BaseWorkflowPlugin

class SoftwareDebugPlugin(BaseWorkflowPlugin):
    @property
    def name(self) -> str:
        return "Software Debugging Suite"

    @property
    def plugin_id(self) -> str:
        return "software_debugging"

    @property
    def description(self) -> str:
        return "Automatically diagnoses code exceptions, reviews logic traces, implements fixes, and runs lint checks."

    def get_custom_system_instruction(self, agent_name: str) -> str:
        if agent_name == "Planner":
            return "You are a Senior Principal Software Architect Planner. Deconstruct coding bugs into diagnostic and fix tasks."
        elif agent_name == "Researcher":
            return "You are an expert technical documentation crawler. Find relevant libraries, error codes, and code samples."
        elif agent_name == "Reasoner":
            return "You are a static code analysis specialist. Map call stacks, identify race conditions or logic errors."
        elif agent_name == "Executor":
            return "You are a Senior Full Stack Engineer. Write clean, bug-free, commented code blocks adhering to SOLID."
        elif agent_name == "Verifier":
            return "You are an QA Automation Lead. Test edge cases, identify syntax risks, and calculate syntax scores."
        return ""

    def get_default_subtasks(self, prompt: str) -> List[Dict[str, Any]]:
        return [
            {
                "title": "Analyze Error Log and Gather Context",
                "description": f"Search documentation, GitHub issues, and StackOverflow for patterns related to: {prompt}",
                "assigned_agent": "researcher",
                "order_index": 0
            },
            {
                "title": "Diagnose Root Cause",
                "description": "Evaluate variable scope, syntax logic, and dependency traces. Explain exactly why the bug occurs and outline the fix strategy.",
                "assigned_agent": "reasoner",
                "order_index": 1
            },
            {
                "title": "Implement and Document Code Fix",
                "description": "Generate clean, commented code addressing the issue. Apply SOLID principles, include edge-case guards, and provide usage examples.",
                "assigned_agent": "executor",
                "order_index": 2
            }
        ]
