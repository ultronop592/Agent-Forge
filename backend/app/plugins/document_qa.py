from typing import Dict, Any, List
from backend.app.plugins.base_plugin import BaseWorkflowPlugin


class DocumentQAPlugin(BaseWorkflowPlugin):
    @property
    def name(self) -> str:
        return "Document QA & Semantic Audit"

    @property
    def plugin_id(self) -> str:
        return "document_qa"

    @property
    def description(self) -> str:
        return (
            "Performs in-depth document extraction, factual verification, cross-referencing against verified memory, "
            "and cited Question-Answering with zero hallucination."
        )

    def get_custom_system_instruction(self, agent_name: str) -> str:
        if agent_name == "Planner":
            return (
                "You are an Information Retrieval & Document Intelligence Architect. Decompose document inquiry requests into "
                "semantic search, passage extraction, factual cross-examination, and cited answer formulation."
            )
        elif agent_name == "Researcher":
            return (
                "You are a Precision Document & Technical Crawler. Search for specific citations, excerpt relevant clauses, "
                "definitions, and exact textual context without truncation."
            )
        elif agent_name == "Reasoner":
            return (
                "You are a Semantic Logic & Contractual Analysis Specialist. Reconcile conflicting statements, interpret technical "
                "terminology, verify logical consistency between clauses, and ensure answers are directly supported by text."
            )
        elif agent_name == "Executor":
            return (
                "You are a Technical Documentation Writer. Formulate precise, authoritative answers with direct textual citations, "
                "structured breakdown, bulleted key takeaways, and explicit confidence boundaries."
            )
        elif agent_name == "Verifier":
            return (
                "You are a Zero-Hallucination Factual Auditor. Verify that every single claim is strictly grounded in cited passages, "
                "check quotation accuracy, flag any extrapolations, and score faithfulness."
            )
        return ""

    def get_default_subtasks(self, prompt: str) -> List[Dict[str, Any]]:
        return [
            {
                "title": "Search Context & Extract Key Passages",
                "description": f"Retrieve relevant documentation, technical specs, and contextual excerpts addressing: {prompt}",
                "assigned_agent": "researcher",
                "order_index": 0
            },
            {
                "title": "Cross-Examine Sources & Fact Reconciliation",
                "description": (
                    "Analyze extracted passages for factual coherence, reconcile conflicting statements, "
                    "and identify exact supporting evidence for each facet of the query."
                ),
                "assigned_agent": "reasoner",
                "order_index": 1
            },
            {
                "title": "Generate Cited Comprehensive Answer",
                "description": (
                    "Construct a clear, definitive response with inline citations, direct quotes, "
                    "key takeaway bullets, and an explicit uncertainty/scope boundary assessment."
                ),
                "assigned_agent": "executor",
                "order_index": 2
            }
        ]
