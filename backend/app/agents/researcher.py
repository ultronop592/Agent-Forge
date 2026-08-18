import json
import logging
from typing import Dict, Any, List
from backend.app.agents.base import BaseAgent
from backend.app.agents.token_budget import compute_token_budget
from backend.app.tools.search import search_web

logger = logging.getLogger("agentforge.agents.researcher")

class ResearcherAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Researcher",
            system_instruction=(
                "You are the Lead Research Agent. Your job is to gather accurate, factual information "
                "from live web search, query external resources, and fetch reference documents.\n"
                "CRITICAL URL & LINK ACCURACY RULES:\n"
                "1. ONLY cite or include a URL if it was explicitly provided verbatim in the live search results.\n"
                "2. NEVER fabricate, hallucinate, construct, or guess URLs (e.g. do not invent links like https://coderound.ai/..., https://example.com/..., or placeholder links).\n"
                "3. If a specific URL was not provided in the search results, state 'Not provided' or omit the link.\n"
                "4. Structure your findings clearly with source titles and verified URLs so downstream agents have grounded facts."
            )
        )

    async def run_subtask(self, subtask_title: str, subtask_desc: str, task_id: str, subtask_id: str) -> str:
        query = subtask_title + " " + subtask_desc
        
        # Log tool call starting
        self.log_db(task_id, subtask_id, "tool_call", f"Executing live search query: '{query[:200]}'")
        
        search_data = await search_web(query, max_results=6)
        results_list = search_data.get("results", [])
        summary_answer = search_data.get("answer", "")
        provider = search_data.get("provider", "none")

        if results_list:
            formatted_results = []
            for r in results_list:
                formatted_results.append(
                    f"Title: {r.get('title')}\nURL: {r.get('url')}\nContent: {r.get('content')}\n---"
                )
            search_output = "\n".join(formatted_results)
            tool_output_summary = f"Gathered {len(results_list)} live web sources via {provider}."
            if summary_answer:
                tool_output_summary += f"\nSummary: {summary_answer}"
            self.log_db(task_id, subtask_id, "output", tool_output_summary)
        else:
            search_output = "No live web search results found for this query."
            self.log_db(task_id, subtask_id, "output", "No search results returned from search providers.")

        prompt = (
            f"You have been assigned the research subtask: {subtask_title}\n"
            f"Subtask Details: {subtask_desc}\n\n"
            f"Live Verified Web Search Results:\n"
            f"{search_output}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Analyze these search results and synthesize a structured research summary.\n"
            f"2. Cite ONLY the real URLs provided in the search results above.\n"
            f"3. Do NOT make up any fake or hypothetical links. If a URL is missing, write 'Not provided'."
        )

        mock_research_doc = (
            f"# Research Summary: {subtask_title}\n\n"
            f"> **Objective:** {subtask_desc}\n\n"
            "## Key Research Findings\n\n"
            f"Findings compiled for **{subtask_title}** based on retrieved search intelligence.\n\n"
            + ("\n".join([f"- **{r.get('title')}**: {r.get('content')[:180]}... ([Source]({r.get('url')}))" for r in results_list]) if results_list else "- No live sources retrieved.")
        )

        token_budget = compute_token_budget(
            subtask_title=subtask_title,
            subtask_desc=subtask_desc,
            agent="researcher",
        )

        output = await self.execute_llm(
            prompt=prompt,
            task_id=task_id,
            subtask_id=subtask_id,
            mock_response_content=mock_research_doc,
            max_output_tokens=token_budget
        )
        return output

