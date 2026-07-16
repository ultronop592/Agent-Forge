"""
analyst_agent.py
Combines the Researcher and Reasoner into a single Analyst Agent.
Saves 1 LLM call by gathering web search results (via Tavily) and performing
critical reasoning / SWOT analysis directly in a single step.
"""
from __future__ import annotations

import json
import logging
import httpx
from typing import Dict, Any, List, Optional
from backend.app.agents.base import BaseAgent
from backend.app.core.config import settings
from backend.app.agents.token_budget import compute_token_budget

logger = logging.getLogger("agentforge.agents.analyst")


class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Analyst",
            system_instruction=(
                "You are the Lead Analyst Agent. Your role is to perform both web research "
                "and critical reasoning in a single step. You synthesize raw search facts "
                "with structural analysis, logical checks, SWOT breakdowns, and tradeoffs.\n"
                "Provide a comprehensive analytical document including:\n"
                "1. Structured research findings with source citations.\n"
                "2. SWOT Analysis & Tradeoff Matrix.\n"
                "3. Contradictions or logic gaps identified and resolved."
            )
        )

    async def _search_tavily(self, query: str) -> Dict[str, Any]:
        """Perform a web search using the Tavily API."""
        tavily_key = settings.tavily_api_key or ""
        if not tavily_key:
            logger.warning("No TAVILY_API_KEY set. Analyst is running search in mock mode.")
            return {"results": [], "answer": "No search API key provided."}

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": tavily_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": True,
            "max_results": 5
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Tavily returned status code {response.status_code}: {response.text}")
                    return {"results": [], "answer": f"Search failed with code {response.status_code}."}
        except Exception as e:
            logger.error(f"Tavily search exception: {e}")
            return {"results": [], "answer": f"Search error: {str(e)}"}

    async def run_subtask(self, subtask_title: str, subtask_desc: str, task_id: str, subtask_id: str) -> str:
        # Use subtask_title as the query to keep it short and highly relevant, avoiding Tavily's 400-char limit
        query = subtask_title[:350]
        
        # Log tool call starting
        self.log_db(task_id, subtask_id, "tool_call", f"Calling Search API with query: '{query}'")

        # 1. Run Search
        search_data = await self._search_tavily(query)
        results = search_data.get("results", [])
        answer = search_data.get("answer", "")

        # Format retrieved content for the LLM
        formatted_sources = ""
        for idx, res in enumerate(results):
            formatted_sources += f"Source [{idx + 1}]: {res.get('title')}\nURL: {res.get('url')}\nContent: {res.get('content')}\n\n"

        self.log_db(task_id, subtask_id, "thinking", f"Retrieved {len(results)} search sources. Beginning synthesis and reasoning...")

        # 2. Compile Prompt
        prompt = (
            f"You have been assigned the subtask: {subtask_title}\n"
            f"Subtask Details: {subtask_desc}\n\n"
            f"Here are the live search results retrieved:\n"
            f"{formatted_sources}\n"
        )
        if answer:
            prompt += f"Summary Answer from search engine: {answer}\n\n"

        prompt += (
            "Analyze the above search data. Conduct critical reasoning, identify logical gaps or contradictions, "
            "perform a SWOT analysis, and output a detailed synthesis report including sources."
        )

        mock_report = (
            f"# Combined Analyst Report: {subtask_title}\n\n"
            f"## 1. Executive Summary & Findings\n"
            f"- Based on web intelligence, AI platforms are shifting toward multi-agent coordination.\n"
            f"- Market sizing projects enterprise workflow automation growing 30% YoY.\n\n"
            f"## 2. SWOT & Critical Tradeoffs Analysis\n"
            f"- **Strengths**: Highly modular, parallel reasoning, self-healing loopbacks.\n"
            f"- **Weaknesses**: Latency increases with sequential gates, API cost overheads.\n"
            f"- **Opportunities**: Tool integrations via MCP, custom workflows.\n"
            f"- **Threats**: Context-window size limits when passing accumulated logs.\n\n"
            f"## 3. Sources Cited\n"
            f"- [1] Forrester Research 2026 (https://forrester.com)\n"
            f"- [2] Gartner Workforce Automation Report (https://gartner.com)\n"
        )

        token_budget = compute_token_budget(
            subtask_title=subtask_title,
            subtask_desc=subtask_desc,
            agent="researcher",  # uses researcher's token budget
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
