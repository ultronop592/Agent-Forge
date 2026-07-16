"""
token_budget.py
Dynamically selects max_output_tokens for each agent call based on the
nature and complexity of the question/subtask.

Tier Map:
  SMALL   →  1 500  (quick facts, simple bug fixes, short code snippets)
  MEDIUM  →  3 000  (structured code, targeted analysis, comparison tables)
  LARGE   →  6 000  (full research reports, market deep-dives, multi-section guides)
  XL      → 10 000  (comprehensive investment memos, full system designs, long-form essays)
"""

from __future__ import annotations
import re

# ---------------------------------------------------------------------------
# Keyword tables — ordered from most specific to most general
# ---------------------------------------------------------------------------

_XL_KEYWORDS = [
    # Long-form deliverables that inherently need depth
    "comprehensive", "in-depth", "detailed report", "full report",
    "investment memo", "business plan", "white paper", "whitepaper",
    "system design", "architecture design", "technical specification",
    "startup analysis", "market analysis", "competitive landscape",
    "literature review", "research paper", "essay",
    "go-to-market", "product roadmap", "strategy document",
    "due diligence",
]

_LARGE_KEYWORDS = [
    # Research / analytical tasks
    "research", "analyze", "analyse", "market size", "market share",
    "competitor", "swot", "trend", "forecast", "industry",
    "deep dive", "deep-dive", "overview", "survey",
    # Code — medium-large size
    "implement", "build", "create", "develop", "design",
    "full implementation", "end-to-end", "production",
    "multi-step", "pipeline", "workflow", "framework",
    # Report-style
    "report", "document", "guide", "tutorial", "walkthrough",
    "explain", "describe in detail",
]

_MEDIUM_KEYWORDS = [
    # Targeted code
    "function", "class", "script", "snippet",
    "refactor", "optimize", "improve",
    # Targeted analysis
    "compare", "contrast", "pros and cons", "trade-off",
    "summarize", "summary", "key points",
    # Debugging
    "debug", "fix", "error", "bug", "issue", "problem",
]

_SMALL_KEYWORDS = [
    # Trivial code / quick facts
    "list", "simple", "quick", "brief", "short",
    "one-liner", "example", "print", "hello world",
    "what is", "definition", "define",
]


def _count_words(text: str) -> int:
    return len(re.findall(r"\w+", text))


def compute_token_budget(
    subtask_title: str = "",
    subtask_desc: str = "",
    context: str = "",
    agent: str = "executor",         # "executor" | "researcher" | "reasoner" | "verifier"
    override: int | None = None,
) -> int:
    """
    Return the recommended max_output_tokens for an agent call.

    Parameters
    ----------
    subtask_title : str
        The short title of the subtask.
    subtask_desc  : str
        The longer description of the subtask.
    context       : str
        Accumulated context from prior agents (used to judge complexity).
    agent         : str
        Which agent is calling — each has a different default ceiling.
    override      : int | None
        If provided, skip all heuristics and return this value directly.
    """
    if override is not None:
        return override

    combined = (subtask_title + " " + subtask_desc).lower()
    word_count = _count_words(combined + " " + context)

    # ── Keyword-based tier detection ────────────────────────────────────────
    tier = _detect_tier(combined)

    # ── Context complexity boost ────────────────────────────────────────────
    # If the accumulated context from prior agents is already very large,
    # the final output should be proportionally detailed.
    if word_count > 1500 and tier == "medium":
        tier = "large"
    if word_count > 3000 and tier == "large":
        tier = "xl"

    # ── Per-agent caps ──────────────────────────────────────────────────────
    # Different agents have different roles:
    #   researcher — always needs room for citations + multi-section structure
    #   reasoner   — logical chains; medium-large
    #   executor   — code or final report; widest range
    #   verifier   — structured JSON + short prose; keep tight
    caps: dict[str, dict[str, int]] = {
        "executor": {
            "small":  1_500,
            "medium": 3_000,
            "large":  6_000,
            "xl":    10_000,
        },
        "researcher": {
            "small":  2_000,    # even "small" research needs citations
            "medium": 4_000,
            "large":  7_000,
            "xl":    10_000,
        },
        "reasoner": {
            "small":  1_200,
            "medium": 2_500,
            "large":  5_000,
            "xl":     8_000,
        },
        "verifier": {
            "small":  1_000,    # JSON + short rationale
            "medium": 1_500,
            "large":  2_000,
            "xl":     2_500,
        },
    }

    agent_caps = caps.get(agent, caps["executor"])
    token_budget = agent_caps.get(tier, agent_caps["medium"])

    return token_budget


def _detect_tier(text: str) -> str:
    """Return 'small' | 'medium' | 'large' | 'xl'."""
    for kw in _XL_KEYWORDS:
        if kw in text:
            return "xl"
    for kw in _LARGE_KEYWORDS:
        if kw in text:
            return "large"
    for kw in _MEDIUM_KEYWORDS:
        if kw in text:
            return "medium"
    for kw in _SMALL_KEYWORDS:
        if kw in text:
            return "small"
    # Default: medium (covers most typical tasks)
    return "medium"
