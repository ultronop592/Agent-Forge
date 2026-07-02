from backend.app.agents.base import BaseAgent

class ReasonerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Reasoner",
            system_instruction=(
                "You are the Lead Reasoning Agent. Your role is to perform critical, logical, "
                "and comparative analysis. You inspect gathered evidence, identify discrepancies, "
                "contradictions, or gaps in information, and build rigorous logical conclusions. "
                "Be skeptical, structured, and logical in your deductions."
            )
        )

    async def run_subtask(self, subtask_title: str, subtask_desc: str, previous_outputs: str, task_id: str, subtask_id: str) -> str:
        prompt = (
            f"You have been assigned the subtask: {subtask_title}\n"
            f"Subtask Details: {subtask_desc}\n\n"
            f"Here is the context and previous agent outputs to analyze:\n"
            f"{previous_outputs}\n\n"
            "Please analyze this data, identify contradictions or logical holes, evaluate key points, and construct a logical synthesis."
        )

        mock_reasoning_doc = (
            f"# Analytical Synthesis: {subtask_title}\n\n"
            f"> **Analysis Scope:** {subtask_desc}\n\n"
            "## 1. Information Consistency Review\n"
            f"Cross-referencing findings for **{subtask_title}** against multiple data points revealed strong "
            "consistency in macro-level trends, with minor divergences in numeric estimates. "
            "All critical references were triangulated with at least two independent sources before being incorporated.\n\n"
            "| Data Point | Source Consistency | Confidence |\n"
            "|------------|-------------------|------------|\n"
            "| Market CAGR (2024–2028) | High — 3 sources agree within ±4% | 92% |\n"
            "| Competitor pricing tiers | Moderate — 2 sources with slight variation | 78% |\n"
            "| Tech adoption signals | High — GitHub stars, survey data aligned | 95% |\n\n"
            "## 2. Logical Gaps and Contradictions Identified\n"
            f"While analyzing data for **{subtask_title}**, the following gaps were detected:\n\n"
            "- **Data Recency Risk**: Some pricing data may be 6–12 months stale. Recommend flagging time-sensitive "
            "figures for live verification before client delivery.\n"
            "- **Vendor Lock-in Blindspot**: Competitive analysis focuses on features but underweights switching costs "
            "and migration complexity — a key decision factor for enterprise buyers.\n"
            "- **Security Posture**: Absence of SOC2 / GDPR compliance data for several competitors creates a blind spot "
            "in regulated-industry use cases (healthcare, finance).\n\n"
            "## 3. SWOT Synthesis\n"
            "**Strengths:** First-mover advantage in agent orchestration; strong OSS community momentum; "
            "modular plugin architecture enabling rapid extensibility.\n\n"
            "**Weaknesses:** Rate-limit constraints on current LLM tiers; limited native observability tooling; "
            "SQLite storage not production-hardened beyond MVP scale.\n\n"
            "**Opportunities:** Enterprise demand for autonomous task pipelines is surging; MCP ecosystem adoption "
            "provides free distribution through third-party integrations.\n\n"
            "**Threats:** Well-funded incumbents (OpenAI, Anthropic) releasing native orchestration tools; "
            "commoditization of base LLM capabilities reducing moat.\n\n"
            "## 4. Structural Recommendations\n"
            "- **Architecture**: Adopt a microservices model to isolate MCP subprocess execution from core API.\n"
            "- **Storage**: Migrate to PostgreSQL for production deployments; use Redis for agent state caching.\n"
            "- **Observability**: Implement OpenTelemetry spans per agent node to trace per-call latency in LangGraph.\n"
        )

        output = await self.execute_llm(
            prompt=prompt,
            task_id=task_id,
            subtask_id=subtask_id,
            mock_response_content=mock_reasoning_doc
        )
        return output
