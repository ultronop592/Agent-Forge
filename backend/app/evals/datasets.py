from typing import List, Optional
from backend.app.evals.rubrics import BenchmarkTestCase

# Standardized benchmark evaluation test suite for AgentForge
BENCHMARK_DATASET: List[BenchmarkTestCase] = [
    # ── Category 1: Coding & Architecture Benchmarks ────────────────────────
    BenchmarkTestCase(
        id="code_01_lru_cache",
        category="coding",
        title="Thread-Safe LRU Cache with TTL Eviction",
        prompt="Design and implement a thread-safe LRU Cache in Python with TTL (Time-To-Live) expiration for entries. Include edge cases, locks, and type annotations.",
        golden_criteria=[
            "Implements O(1) get and put operations via Doubly Linked List + Hash Map or OrderedDict.",
            "Thread-safe using threading.Lock or threading.RLock.",
            "Enforces TTL expiration upon retrieval or proactive purge.",
            "Contains clean docstrings, usage examples, and SOLID principles."
        ],
        expected_output_type="code",
        difficulty="medium"
    ),
    BenchmarkTestCase(
        id="code_02_distributed_rate_limiter",
        category="coding",
        title="Sliding Window Rate Limiter",
        prompt="Write a Python sliding window log rate limiter class supporting per-client request quotas with timestamp tracking and graceful fallback handling.",
        golden_criteria=[
            "Sliding window algorithm correctly purges expired timestamps.",
            "Thread-safe / race-condition guarded.",
            "Provides is_allowed(client_id) method returning boolean and remaining quota.",
            "Handles edge cases (first request, clock drift, capacity limits)."
        ],
        expected_output_type="code",
        difficulty="hard"
    ),
    BenchmarkTestCase(
        id="code_03_sql_connection_pool_fix",
        category="coding",
        title="Diagnose & Fix Async Database Connection Leak",
        prompt="Debug a connection leak in an async SQLAlchemy engine where sessions remain in idle-in-transaction status under high load. Provide the root cause and a production fix.",
        golden_criteria=[
            "Identifies missing session.close() / context manager rollback as root cause.",
            "Provides pool_pre_ping=True, pool_size, and max_overflow configuration.",
            "Provides async context manager wrapper with robust exception handling.",
            "Includes unit tests testing pool exhaustion recovery."
        ],
        expected_output_type="code",
        difficulty="medium"
    ),

    # ── Category 2: Market & Strategic Research Benchmarks ──────────────────
    BenchmarkTestCase(
        id="research_01_ai_code_assistants",
        category="research",
        title="AI Coding Assistants Market Intelligence",
        prompt="Perform a competitive market research analysis on the AI Coding Assistant landscape (Cursor, Copilot, Windsurf, Devin). Include TAM/SAM/SOM sizing, competitor matrix, SWOT, and defensibility.",
        golden_criteria=[
            "Detailed competitor matrix comparing features, latency, pricing, and enterprise controls.",
            "TAM / SAM / SOM market sizing calculations with realistic projections.",
            "Critical 4-quadrant SWOT matrix.",
            "Actionable strategic roadmap and risk register."
        ],
        expected_output_type="report",
        difficulty="medium"
    ),
    BenchmarkTestCase(
        id="research_02_vector_db_comparison",
        category="research",
        title="Vector Database Comparison for Agentic RAG",
        prompt="Conduct a technical and financial trade-off analysis comparing pgvector (Neon/Postgres), Pinecone, and Qdrant for enterprise multi-agent retrieval. Provide latency benchmarks and TCO.",
        golden_criteria=[
            "Compares indexing algorithms (HNSW vs IVFFlat).",
            "Analyzes Total Cost of Ownership (TCO) across query volume tiers.",
            "Evaluates hybrid search capabilities (Full-text BM25 + Dense Vectors).",
            "Provides clear architectural recommendation for production agent workloads."
        ],
        expected_output_type="report",
        difficulty="hard"
    ),

    # ── Category 3: Multi-Step Reasoning & Problem Decomposition ───────────
    BenchmarkTestCase(
        id="reasoning_01_incident_postmortem",
        category="reasoning",
        title="Site Reliability Engineering Incident Postmortem",
        prompt="Create an SRE postmortem for a cascading microservices failure caused by an unauthenticated Redis worker queue breach. Include 5-Whys root cause, timeline, and preventive guardrails.",
        golden_criteria=[
            "Realistic incident timeline from initial breach to remediation.",
            "Rigorous 5-Whys root cause analysis.",
            "Actionable short-term and long-term preventive action items.",
            "Defines SLI/SLA impact and MTTD/MTTR metrics."
        ],
        expected_output_type="report",
        difficulty="medium"
    ),
]


def get_benchmark_by_id(benchmark_id: str) -> Optional[BenchmarkTestCase]:
    """Retrieve a benchmark test case by ID."""
    for b in BENCHMARK_DATASET:
        if b.id == benchmark_id:
            return b
    return None


def get_benchmarks_by_category(category: str) -> List[BenchmarkTestCase]:
    """Filter benchmarks by category ('coding', 'research', 'reasoning', or 'all')."""
    if not category or category.lower() == "all":
        return BENCHMARK_DATASET
    return [b for b in BENCHMARK_DATASET if b.category.lower() == category.lower()]
