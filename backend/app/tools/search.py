"""
search.py
Robust multi-provider web search tool for AgentForge agents.
Integrates Tavily API with automatic DuckDuckGo live web search fallback,
ensuring agents always receive genuine, verifiable URLs and snippets from the real web.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from typing import Any, Dict, List
import httpx
from backend.app.core.config import settings

logger = logging.getLogger("agentforge.tools.search")

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


async def search_web(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search the web using Tavily (if configured) with DuckDuckGo fallback.
    Returns:
        {
            "provider": "tavily" | "duckduckgo" | "none",
            "results": [
                {
                    "title": str,
                    "url": str,
                    "content": str
                },
                ...
            ],
            "answer": str (optional summary)
        }
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return {"provider": "none", "results": [], "answer": "Empty query."}

    # 1. Try Tavily API if key is present
    tavily_key = settings.tavily_api_key or ""
    if tavily_key:
        try:
            tavily_res = await _search_tavily(cleaned_query, tavily_key, max_results)
            if tavily_res.get("results"):
                return tavily_res
        except Exception as e:
            logger.warning(f"Tavily search failed, falling back to DuckDuckGo: {e}")

    # 2. Try DuckDuckGo live HTML search fallback
    try:
        ddg_res = await _search_duckduckgo(cleaned_query, max_results)
        if ddg_res.get("results"):
            return ddg_res
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")

    return {
        "provider": "none",
        "results": [],
        "answer": "No live search results could be retrieved from search providers."
    }


async def _search_tavily(query: str, api_key: str, max_results: int) -> Dict[str, Any]:
    """Execute search query against Tavily API."""
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query[:400],
        "search_depth": "advanced",
        "include_answer": True,
        "max_results": max_results
    }
    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            raw_results = data.get("results", [])
            results = []
            for item in raw_results[:max_results]:
                url_str = item.get("url", "")
                if url_str and url_str.startswith("http"):
                    results.append({
                        "title": item.get("title", "Web Result"),
                        "url": url_str,
                        "content": item.get("content", "")
                    })
            return {
                "provider": "tavily",
                "results": results,
                "answer": data.get("answer", "")
            }
        else:
            logger.warning(f"Tavily returned code {resp.status_code}: {resp.text[:200]}")
            return {"provider": "tavily", "results": [], "answer": ""}


async def _search_duckduckgo(query: str, max_results: int) -> Dict[str, Any]:
    """
    Execute search query against DuckDuckGo HTML search.
    Parses real search result titles, real URLs, and real snippet texts.
    """
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    data = {"q": query[:300]}

    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        resp = await client.post(url, data=data, headers=headers)
        if resp.status_code != 200:
            logger.warning(f"DuckDuckGo returned status {resp.status_code}")
            return {"provider": "duckduckgo", "results": [], "answer": ""}

        html = resp.text

        # Extract result blocks from DuckDuckGo HTML
        # Match links with class result__url or result__a
        results = []

        # Find result containers
        # Patterns for titles, URLs, and snippets in DDG HTML
        result_blocks = re.findall(
            r'<div[^>]*class="[^"]*result[^"]*"[^>]*>(.*?)</div>\s*(?=<div[^>]*class="[^"]*result[^"]*"|$)',
            html,
            re.DOTALL | re.IGNORECASE
        )

        for block in result_blocks:
            if len(results) >= max_results:
                break

            # Extract link href and title
            link_match = re.search(
                r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                block,
                re.DOTALL | re.IGNORECASE
            )
            if not link_match:
                continue

            raw_href = link_match.group(1).strip()
            raw_title = link_match.group(2).strip()

            # DuckDuckGo wraps target URLs in /l/?uddg=...
            actual_url = raw_href
            if "uddg=" in raw_href:
                uddg_part = raw_href.split("uddg=")[1].split("&")[0]
                actual_url = urllib.parse.unquote(uddg_part)
            elif raw_href.startswith("//"):
                actual_url = "https:" + raw_href

            # Clean tags from title
            clean_title = re.sub(r'<[^>]+>', '', raw_title).strip()

            # Extract snippet
            snippet_match = re.search(
                r'<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
                block,
                re.DOTALL | re.IGNORECASE
            )
            clean_snippet = ""
            if snippet_match:
                clean_snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()

            if actual_url.startswith("http") and clean_title:
                results.append({
                    "title": clean_title,
                    "url": actual_url,
                    "content": clean_snippet or clean_title
                })

        return {
            "provider": "duckduckgo",
            "results": results,
            "answer": ""
        }
