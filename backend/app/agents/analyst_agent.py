"""
analyst_agent.py
Combines the Researcher and Reasoner into a single Analyst Agent.
Saves 1 LLM call by gathering live web search results and performing
critical reasoning / SWOT analysis directly in a single step with strict URL grounding.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Optional
from backend.app.agents.base import BaseAgent
from backend.app.tools.search import search_web
from backend.app.agents.token_budget import compute_token_budget

logger = logging.getLogger("agentforge.agents.analyst")


class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Analyst",
            system_instruction=(
                "You are the Lead Analyst Agent. Your role is to perform both web research "
                "and critical reasoning in a single step. You synthesize live search facts "
                "with structural analysis, logical checks, SWOT breakdowns, and tradeoffs.\n"
                "CRITICAL URL & LINK ACCURACY RULES:\n"
                "1. ONLY cite or include a URL if it was explicitly provided verbatim in the live search results.\n"
                "2. NEVER fabricate, hallucinate, construct, or guess URLs.\n"
                "3. If a specific URL was not provided in the search results, state 'Not provided' or omit the link.\n"
                "Provide a comprehensive analytical document including:\n"
                "1. Structured research findings with genuine source citations.\n"
                "2. SWOT Analysis & Tradeoff Matrix.\n"
                "3. Contradictions or logic gaps identified and resolved."
            )
        )

    async def run_subtask(self, subtask_title: str, subtask_desc: str, task_id: str, subtask_id: str) -> str:
        query = (subtask_title + " " + subtask_desc)[:350]
        
        # Log tool call starting
        self.log_db(task_id, subtask_id, "tool_call", f"Executing live search query: '{query[:200]}'")

        # 1. Run Search
        search_data = await search_web(query, max_results=6)
        results = search_data.get("results", [])
        answer = search_data.get("answer", "")
        provider = search_data.get("provider", "none")

        # Format retrieved content for the LLM
        formatted_sources = ""
        if results:
            for idx, res in enumerate(results):
                formatted_sources += (
                    f"Source [{idx + 1}]: {res.get('title')}\n"
                    f"URL: {res.get('url')}\n"
                    f"Content: {res.get('content')}\n\n"
                )
            self.log_db(task_id, subtask_id, "thinking", f"Retrieved {len(results)} live search sources via {provider}. Synthesizing...")
        else:
            formatted_sources = "No live web search results found for this query."
            self.log_db(task_id, subtask_id, "thinking", "No search results returned. Synthesizing from factual knowledge without inventing links...")

        # 2. Compile Prompt
        prompt = (
            f"You have been assigned the subtask: {subtask_title}\n"
            f"Subtask Details: {subtask_desc}\n\n"
            f"Here are the live verified search results retrieved:\n"
            f"{formatted_sources}\n"
        )
        if answer:
            prompt += f"Summary Answer from search engine: {answer}\n\n"

        prompt += (
            "Analyze the above search data. Conduct critical reasoning, identify logical gaps or contradictions, "
            "perform a SWOT analysis, and output a detailed synthesis report.\n"
            "STRICT RULE: Include only genuine URLs from the search results above. Do not invent any URLs."
        )

        mock_report = (
            f"# Combined Analyst Report: {subtask_title}\n\n"
            f"## 1. Executive Summary & Findings\n"
            f"- Analysis compiled for **{subtask_title}**.\n\n"
            + ("\n".join([f"- **{r.get('title')}**: {r.get('content')[:180]}... ([Link]({r.get('url')}))" for r in results]) if results else "- No live sources retrieved.")
            + "\n\n## 2. SWOT & Critical Tradeoffs Analysis\n"
            "- **Strengths**: Highly modular workflow orchestration.\n"
            "- **Weaknesses**: External API rate constraints.\n"
            "- **Opportunities**: Tool integrations via MCP.\n"
            "- **Threats**: Rapid evolution of ecosystem specifications.\n"
        )

        token_budget = compute_token_budget(
            subtask_title=subtask_title,
            subtask_desc=subtask_desc,
            agent="researcher",
        )

        # 3. Call LLM for single-step synthesis & reasoning
        output = await self.execute_llm(
            prompt=prompt,
            task_id=task_id,
            subtask_id=subtask_id,
            mock_response_content=mock_report,
            max_output_tokens=token_budget
        )
        return output
