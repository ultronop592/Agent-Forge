from typing import Dict, Any, List
from backend.app.plugins.base_plugin import BaseWorkflowPlugin


class CodeReviewPlugin(BaseWorkflowPlugin):
    @property
    def name(self) -> str:
        return "Production Code Review & Security Audit"

    @property
    def plugin_id(self) -> str:
        return "code_review"

    @property
    def description(self) -> str:
        return (
            "Conducts rigorous static code analysis, security vulnerability scanning (OWASP Top 10), "
            "performance profiling, architectural design review, and refactored code delivery."
        )

    def get_custom_system_instruction(self, agent_name: str) -> str:
        if agent_name == "Planner":
            return (
                "You are a Senior Engineering Director & Staff Architect. Structure code review objectives into "
                "security vulnerability scanning, performance bottleneck analysis, clean code review, and refactoring."
            )
        elif agent_name == "Researcher":
            return (
                "You are a Security Vulnerability & Dependency Auditor. Search for CVE databases, OWASP security advisories, "
                "memory safety guidelines, and modern language best practice specs."
            )
        elif agent_name == "Reasoner":
            return (
                "You are a Principal Static Analysis Specialist. Analyze algorithmic time/space complexity (Big-O), "
                "identify race conditions, detect memory leaks, verify error handling boundaries, and review SOLID design patterns."
            )
        elif agent_name == "Executor":
            return (
                "You are a Senior Staff Software Engineer. Produce comprehensive code review diffs, rewrite problematic functions "
                "with idiomatic patterns, add type annotations, docstrings, and comprehensive unit tests."
            )
        elif agent_name == "Verifier":
            return (
                "You are a Quality Assurance & Security Gatekeeper. Scrutinize refactored code for regressions, "
                "verify edge cases (null inputs, boundary conditions, concurrent access), and evaluate security hardening."
            )
        return ""

    def get_default_subtasks(self, prompt: str) -> List[Dict[str, Any]]:
        return [
            {
                "title": "Static Code Audit & Security Vulnerability Scan",
                "description": (
                    f"Scan code for OWASP Top 10 risks, insecure dependencies, boundary overflows, "
                    f"unhandled exceptions, and concurrency issues: {prompt}"
                ),
                "assigned_agent": "researcher",
                "order_index": 0
            },
            {
                "title": "Algorithmic Complexity & Architecture Review",
                "description": (
                    "Evaluate time/space complexity (Big-O), thread safety, resource lifecycles, and architectural compliance "
                    "with SOLID principles. Provide itemized critique with severity ratings."
                ),
                "assigned_agent": "reasoner",
                "order_index": 1
            },
            {
                "title": "Refactored Implementation & Unit Test Suite",
                "description": (
                    "Provide production-ready refactored code incorporating all review recommendations, full type annotations, "
                    "defensive guards, and a robust test suite covering edge cases."
                ),
                "assigned_agent": "executor",
                "order_index": 2
            }
        ]
