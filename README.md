# AgentForge

## Autonomous Multi-Agent Workforce Platform

AgentForge is an enterprise-grade autonomous AI workforce system engineered for orchestrating coordinated teams of specialized agents that plan, research, execute, and verify complex technical and analytical tasks. Rather than relying on a single generalist prompt, AgentForge decomposes user objectives into structured subtask pipelines, delegates each phase to a dedicated role specialist, and delivers fully verified deliverables with real-time progress streaming.

The platform operates in production environments with self-healing verification loops, event-driven human-in-the-loop control gates, an isolated runtime execution harness enforcing resource limits and tool permissions, cross-task 768-dimensional vector memory, extensibility through the Model Context Protocol, and comprehensive telemetry observability.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Platform Architecture](#platform-architecture)
3. [Agent Workforce](#agent-workforce)
4. [Workflow State Machine](#workflow-state-machine)
5. [Event-Driven Human-in-the-Loop Control Gates](#event-driven-human-in-the-loop-control-gates)
6. [Runtime Harness and Resource Guardrails](#runtime-harness-and-resource-guardrails)
7. [Vector Memory System](#vector-memory-system)
8. [Model Context Protocol Integration](#model-context-protocol-integration)
9. [Workflow Plugin Engine](#workflow-plugin-engine)
10. [Token Budget Engine](#token-budget-engine)
11. [Telemetry, Observability, and Pricing](#telemetry-observability-and-pricing)
12. [LLM-as-Judge Evaluation Framework](#llm-as-judge-evaluation-framework)
13. [Security Architecture](#security-architecture)
14. [Database Architecture and Migration](#database-architecture-and-migration)
15. [Database Schema](#database-schema)
16. [API Reference](#api-reference)
17. [Frontend Architecture](#frontend-architecture)
18. [Performance Engineering](#performance-engineering)
19. [Technology Stack](#technology-stack)
20. [Repository Structure](#repository-structure)
21. [Configuration Reference](#configuration-reference)
22. [Local Development and Operations](#local-development-and-operations)

---

## System Overview

AgentForge structures execution as a deterministic, stateful multi-agent pipeline. Each agent in the workforce represents an isolated operational role with specialized system instructions, dedicated token allocation boundaries, and independent telemetry accounting.

### Core Architectural Principles

- **Deterministic Graph Orchestration**: All agent routing is managed by a LangGraph StateGraph compiled at system startup. The routing logic is pure, conditional, and testable in isolation. No implicit agent chaining or hidden tool calls occur outside the state graph.
- **Runtime Execution Guardrails**: Every task executes inside an AgentHarness that tracks steps, wall-clock duration, dollar expenditure, and token consumption against configurable hard limits. Agents operate under a strict least-privilege tool allowlist.
- **Self-Healing Quality Loops**: The Verifier agent evaluates every deliverable against a structured five-dimension rubric. If the composite confidence score falls below 0.80, the graph routes back to the Executor with targeted correction feedback. This loop repeats up to three times before halting.
- **Zero-Cost Supervisor**: The Manager Agent oversees pipeline execution without invoking any LLMs. All routing announcements, parallel dispatch logs, and final run summaries are written directly to the database as structured log entries at zero AI API cost.
- **Event-Driven Human Control Points**: Two human-in-the-loop gates allow human operators to review, modify, or steer execution. Gates utilize an asynchronous event registry (`GateRegistry`) for immediate resumption on user action, paired with a five-second database fallback check and configurable timeouts.
- **Real-Time Task Cancellation**: Active tasks can be halted immediately via a dedicated task registry (`TaskRegistry`), which cancels the underlying asynchronous task and stops in-flight LLM calls.
- **Standardized Vector Memory**: Completed tasks are archived as 768-dimensional, L2-normalized vector embeddings in PostgreSQL (using pgvector) or SQLite. Future runs query this store using cosine similarity to retrieve relevant historical solutions before execution begins.

---

## Platform Architecture

The following diagram illustrates the complete AgentForge platform topology, detailing data flow from client interaction through the API layer, execution harness, LangGraph orchestrator, database storage, and external AI services.

```
+---------------------------------------------------------------------------------------+
|                                  AGENTFORGE PLATFORM                                  |
+---------------------------------------------------------------------------------------+
                                           |
       +-----------------------------------+-----------------------------------+
       |                                                                       |
       v                                                                       v
+-------------------------------+                               +-------------------------------+
|       Next.js Frontend        |                               |       FastAPI Backend         |
|       (React 19, SSE)         |                               |       (REST & SSE Stream)     |
+-------------------------------+                               +-------------------------------+
       |                 ^                                             |                 ^
       | HTTP Actions    | Server-Sent Events                          | ORM Queries     | Vector Match
       v                 |                                             v                 |
+-------------------------------+                               +-------------------------------+
| REST API Endpoints            |                               | Dual Storage Layer            |
| - /api/tasks                  |                               | - PostgreSQL + pgvector (768) |
| - /api/tasks/{id}/stream      |                               | - SQLite Fallback             |
| - /api/mcp                    |                               | - HNSW Cosine Index           |
+-------------------------------+                               +-------------------------------+
       |
       v
+---------------------------------------------------------------------------------------+
|                              TASK RUNNER & RUNTIME HARNESS                            |
|                                                                                       |
|  AgentHarness: Step Limits | Wall-Clock Time | Token Budget | Cost Cap | Tool Allowlist|
|  TaskRegistry: In-flight asyncio.Task registration, tracking, and hard cancellation   |
|  GateRegistry: Asynchronous event signaling (open, signal, close) for HITL gates      |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                                LANGGRAPH STATEGRAPH                                   |
|                                                                                       |
|                    +------------------------------------+                             |
|                    |           Planner Agent            |                             |
|                    +------------------------------------+                             |
|                                      |                                                |
|                                      v                                                |
|                    +------------------------------------+                             |
|                    |     Plan Approval Gate (HITL)      |                             |
|                    +------------------------------------+                             |
|                                      |                                                |
|                  +-------------------+-------------------+                            |
|                  |                                       |                            |
|                  v                                       v                            |
|    +---------------------------+           +---------------------------+              |
|    |    Parallel Research      |           |     Sequential Agent      |              |
|    |    (Memory + Analyst)     |           |     (Analyst / Memory)    |              |
|    +---------------------------+           +---------------------------+              |
|                  |                                       |                            |
|                  +-------------------+-------------------+                            |
|                                      |                                                |
|                                      v                                                |
|                    +------------------------------------+                             |
|                    |          Executor Agent            |<-------------------+        |
|                    +------------------------------------+                    |        |
|                                      |                                       |        |
|                                      v                                       |        |
|                    +------------------------------------+                    |        |
|                    |          Verifier Agent            |                    |        |
|                    +------------------------------------+                    |        |
|                                      |                                       |        |
|                                      v                                       |        |
|                    +------------------------------------+                    |        |
|                    |  Valid Deliverable / Score >= 0.8? |--- No (Retries < 3)+        |
|                    +------------------------------------+ (Steering Gate Intercept)   |
|                                      |                                                |
|                                      | Yes (or Retries Exhausted)                     |
|                                      v                                                |
|                    +------------------------------------+                             |
|                    |  Archive Memory (768-dim Vector)   |                             |
|                    |  Deliver Final Verified Result     |                             |
|                    +------------------------------------+                             |
+---------------------------------------------------------------------------------------+
       |                                   |                                   |
       v                                   v                                   v
+------------------+              +------------------+              +------------------+
|  Google Gemini   |              |  Tavily Search   |              | Model Context    |
|  2.5 Flash LLM   |              |  API             |              | Protocol (MCP)   |
|  Embedding-001   |              |  (Live Web)      |              | JSON-RPC 2.0     |
+------------------+              +------------------+              +------------------+
```

---

## Agent Workforce

The AgentForge workforce comprises six specialized agent roles, each purpose-built for a specific phase of the task lifecycle.

### Planner Agent
- **Role**: Decomposes raw user goals into an ordered pipeline of machine-parseable subtasks.
- **Execution Mechanism**: Generates structured Pydantic schemas validating subtask title, description, and designated downstream agent.
- **Constraints**: Operates with a zero-tool allowlist. Tool calls from this agent are denied by the runtime harness.

### Manager Agent
- **Role**: Zero-cost supervisor that coordinates pipeline execution, tracks state transitions, and emits audit logs.
- **Execution Mechanism**: Makes zero LLM calls. All announcements, dispatch notices, parallel execution markers, and final run summaries are written directly to the `agent_logs` table as `manager_decision` entries.
- **Cost Footprint**: Exactly $0.00 in LLM charges across all task runs.

### Memory Agent
- **Role**: Institutional memory retrieval and semantic recall.
- **Execution Mechanism**: Calculates 768-dimensional L2-normalized embeddings via Google `gemini-embedding-001` with `output_dimensionality=768`. Performs vector cosine similarity searches over historical records, returning the top five relevant solutions scoring above a 0.45 similarity threshold.
- **Optimization**: Uses vectorized NumPy operations where available, with a pure Python arithmetic fallback. The query embedding is cached in `AgentState.prompt_embedding` and reused when archiving the final deliverable, eliminating a second embedding API call.
- **Permissions**: Authorized exclusively for `memory_search`.

### Analyst Agent
- **Role**: Live web intelligence gathering and strategic reasoning.
- **Execution Mechanism**: Consolidates external search and analytical reasoning into a single unified LLM invocation. Queries the Tavily Search API, ingests current web context, and synthesizes structured findings (including SWOT analyses and risk matrices).
- **Optimization**: Eliminates the previous two-call separation (search followed by reasoning), reducing pipeline latency by six seconds.
- **Permissions**: Authorized exclusively for `tavily_search`.

### Executor Agent
- **Role**: Primary deliverable construction and synthesis.
- **Execution Mechanism**: Ingests the cumulative output of all upstream agents, historical memory context, the original user goal, and any Verifier correction feedback from previous retry attempts to generate the complete deliverable.
- **Context Guardrail**: Implements an 8,000-character context truncation threshold. Inputs exceeding this limit are cleanly sliced at line boundaries with an explicit truncation annotation, preventing context window saturation while preserving complete records in state.
- **Permissions**: Zero MCP tools authorized by default. Permissions can be extended through workflow plugins.

### Verifier Agent
- **Role**: Independent quality control, rubric scoring, link verification, and self-healing feedback generation.
- **Execution Mechanism**: Evaluates the Executor's deliverable against a five-dimensional rubric. Calculates an overall confidence score (0.00 to 1.00). If the score is below 0.80, generates structured, actionable correction guidance and triggers a self-healing retry.
- **Link Sanitization**: Scans output text for fabricated, placeholder, or dead URLs, stripping or replacing them with verified sources.
- **Constraints**: Zero-tool allowlist. Operates purely on prompt context.

### Additional Workforce Roles
- **Researcher Agent**: Standalone deep-dive information retrieval agent available for specialized plugin configurations.
- **Reasoner Agent**: Standalone critical evaluation and logical deduction agent available for complex analytical plugins.

---

## Workflow State Machine

The orchestration engine uses LangGraph StateGraph, compiled as a directed graph with one bounded retry cycle.

### AgentState Schema

The shared execution context is modeled as a TypedDict (`AgentState`) passed between graph nodes:

| State Key | Type | Description |
|---|---|---|
| `task_id` | `str` | Unique UUID identifier for the active task |
| `prompt` | `str` | Original user objective |
| `plugin_name` | `str` | Active workflow plugin identifier |
| `subtasks` | `List[Dict]` | Ordered list of subtask records |
| `current_subtask_index` | `int` | Execution pointer indicating current active subtask |
| `agent_outputs` | `Dict[str, str]` | Mapping of subtask identifier to agent output text |
| `verification_results` | `Dict[str, Any]` | Verifier composite score, dimension ratings, and feedback |
| `final_result` | `str` | Final verified deliverable |
| `retry_count` | `int` | Number of Verifier-triggered self-healing retries executed |
| `verifier_feedback` | `str` | Diagnostic feedback from the most recent verification pass |
| `prompt_embedding` | `List[float]` | Cached 768-dimensional L2-normalized query vector |
| `agent_sequence` | `List[str]` | Ordered execution history of agents for audit reporting |
| `manager_quality_scores`| `Dict[str, float]`| Quality scores recorded by the Manager per subtask |
| `manager_skip_flags` | `Dict[str, bool]` | Flags marking subtasks skipped due to budget limits |
| `agent_retry_counts` | `Dict[str, int]` | Individual retry attempt counters per subtask |

### Graph Topology and Routing Flow

```
                      +-------------------+
                      |    Entry Point    |
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |      planner      |
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |   route_subtasks  |
                      +-------------------+
                                |
         +----------------------+----------------------+----------------------+
         |                      |                      |                      |
         v                      v                      v                      v
+------------------+   +------------------+   +------------------+   +------------------+
| parallel_research|   |   memory_agent   |   |     analyst      |   |     executor     |
+------------------+   +------------------+   +------------------+   +------------------+
         |                      |                      |                      |
         +----------------------+----------------------+                      |
                                |                                             |
                                v                                             |
                      +-------------------+                                   |
                      |   route_subtasks  |<----------------------------------+
                      +-------------------+
                                |
                                | (All Subtasks Consumed)
                                v
                      +-------------------+
                      |     verifier      |
                      +-------------------+
                                |
                                v
                      +-------------------+
                      | route_verifier    |
                      +-------------------+
                                |
                +---------------+---------------+
                |                               |
                v                               v
       +------------------+            +------------------+
       |     executor     |            |     __end__      |
       |  (Retry < 3)     |            | (Score >= 0.80   |
       +------------------+            |  or Retries = 3) |
                                       +------------------+
```

### Parallel Research Routing
When `route_subtasks` identifies two or more consecutive research-type subtasks (`memory_agent` or `analyst`) starting at `current_subtask_index`, it routes execution to `parallel_research`. This node executes both subtasks concurrently using `asyncio.gather`, aggregates their results into `AgentState.agent_outputs`, and updates the subtask index pointer before returning to the router.

### LLM Call Budget Accounting
- **Clean First Pass**: Exactly 5 LLM calls:
  1. Planner (subtask decomposition)
  2. Memory Agent (768-dim query embedding)
  3. Analyst (live web research and SWOT synthesis)
  4. Executor (deliverable generation)
  5. Verifier (rubric evaluation and QA)
- **Per Self-Healing Retry**: Exactly 2 additional LLM calls:
  1. Executor (synthesis with correction guidance)
  2. Verifier (re-evaluation)
- **Worst-Case Ceiling**: Maximum 11 LLM calls across the maximum allowed 3 retries, plus any automatic retries triggered by rate limit encounters (HTTP 429).

---

## Event-Driven Human-in-the-Loop Control Gates

AgentForge provides two control gates that allow operators to review, edit, or steer execution. These gates operate without inefficient polling loops by leveraging an asynchronous event registry (`GateRegistry`).

### GateRegistry Architecture

The `GateRegistry` maintains an active `asyncio.Event` mapped to each running `task_id`:
- `open(task_id)`: Initializes a new event for the task.
- `signal(task_id)`: Triggers the event immediately upon user action.
- `close(task_id)`: Cleans up the event mapping once the gate unblocks.

```
Orchestrator Gate Wait                         API Endpoint (/approve_plan, /steer, /reject)
         |                                                                |
         |--- GateRegistry.open(task_id)                                  |
         |--- asyncio.wait_for(event.wait(), timeout=HITL_TIMEOUT)        |
         |    [Fallback: DB check every 5s]                               |
         |                                                                |
         |                                <--- User submits action -------|
         |                                     POST /tasks/{id}/approve   |
         |                                                                |
         |                                     GateRegistry.signal(task_id)
         |<-- asyncio.Event set immediately ------------------------------|
         |
         |--- GateRegistry.close(task_id)
         v
Resume Orchestrator Execution
```

### Plan Approval Gate
- **Trigger**: Occurs immediately after the Planner generates the subtask pipeline.
- **Status**: The task transitions to `awaiting_plan_approval`.
- **Operator Actions**:
  - Edit subtask titles and descriptions inline.
  - Reorder subtasks.
  - Reassign subtasks to different agents.
  - Insert new custom subtasks or delete existing ones.
  - Approve the plan via `POST /api/tasks/{task_id}/approve_plan`.
  - Reject the plan via `POST /api/tasks/{task_id}/reject`.
- **Immediate Signaling**: Invoking the approval or rejection endpoint calls `GateRegistry.signal()`, waking the orchestrator instantly without delay.
- **Fallback & Timeout**: If no operator action occurs before `HITL_TIMEOUT_SECONDS` (default: 60.0s), the gate auto-proceeds with the current plan. A fallback check queries the database status every 5 seconds to handle out-of-band updates.

### Mid-Execution Steering Gate
- **Trigger**: Occurs when the Verifier rejects a deliverable (confidence score < 0.80) and a self-healing retry is scheduled.
- **Status**: The task transitions to `awaiting_steering`.
- **Operator Actions**:
  - Submit targeted steering instructions via `POST /api/tasks/{task_id}/steer` to be injected into the Executor's next prompt.
  - Force-accept the deliverable as complete.
  - Cancel execution entirely.
- **Immediate Signaling**: Calling `/steer` signals the `GateRegistry` event, immediately waking the retry cycle.
- **Timeout**: If no steering input is received within the timeout window, the gate auto-proceeds using the Verifier's diagnostic feedback as the correction guidance.

### Active Task Cancellation
When a task is rejected via `POST /api/tasks/{task_id}/reject`:
1. The endpoint retrieves the active `asyncio.Task` registered in `TaskRegistry`.
2. It invokes `task.cancel()`, immediately terminating in-flight LLM calls and network operations.
3. The task record is updated to `cancelled`, and a final SSE event is emitted.

---

## Runtime Harness and Resource Guardrails

The `backend/app/harness/` module provides a runtime sandbox that enforces resource limits and tool execution permissions across every task.

```
                    +------------------------------------+
                    |        Task Runner Invoked         |
                    +------------------------------------+
                                      |
                                      v
                    +------------------------------------+
                    |  Initialize AgentHarness Instance  |
                    |  - Load RunLimits from Config      |
                    |  - Load Tool Permissions Allowlist |
                    |  - Register in TaskRegistry        |
                    +------------------------------------+
                                      |
                                      v
                    +------------------------------------+
                    | Graph Node: harness.before_step()  |
                    +------------------------------------+
                                      |
                         +------------+------------+
                         |                         |
              Limits Respected              Limit Exceeded
                         |                         |
                         v                         v
               +-------------------+     +--------------------------------+
               | Execute Agent     |     | Raise BudgetExceeded(reason)   |
               +-------------------+     +--------------------------------+
                         |                                 |
                         v                                 v
               +-------------------+             +-------------------+
               | Tool Invocation:  |             | Task Status Failed|
               | harness.authorize |             | Save Snapshot to  |
               +-------------------+             | failure_reason    |
                         |                       | Manager Log Entry |
                         v                       | SSE Terminal Event|
               +-------------------+             +-------------------+
               | BaseAgent:        |                       |
               | harness.record()  |                       v
               +-------------------+             +-------------------+
                         |                       | Pipeline Halts    |
                         v                       +-------------------+
               +-------------------+
               | Proceed to Next   |
               | State Node        |
               +-------------------+
```

### Resource Limits (`RunLimits`)

Hard limits are configured via the `RunLimits` schema with standard production defaults, overridable through environment variables:

| Limit Dimension | Default Value | Environment Variable | Enforcement Mechanism |
|---|---|---|---|
| Step Count | 25 steps | `HARNESS_MAX_STEPS` | Checked in `before_step()`. Each graph node and Verifier retry increments the counter. |
| Active Execution Duration | 300.0 seconds | `HARNESS_MAX_SECONDS` | Active elapsed time calculated excluding paused HITL gate intervals in `before_step()`. |
| Paused Human Duration | None (Disabled) | `HARNESS_MAX_PAUSED_SECONDS` | Optional cumulative safety cap on time spent paused awaiting human review. |
| Cost Expenditure | $0.50 USD | `HARNESS_MAX_COST_USD` | Accumulated after every LLM call via `record()` and checked in `before_step()`. |
| Token Consumption | 120,000 tokens | `HARNESS_MAX_TOKENS` | Accumulated prompt and completion tokens via `record()` and checked in `before_step()`. |

### Tool Permissions Model

Every agent operates under an explicit least-privilege tool allowlist configured in `harness/permissions.py`:

| Agent Role | Default Allowed Tools | Tool Denial Behavior |
|---|---|---|
| Planner | None | Raises `ToolDenied` on any tool call attempt |
| Analyst | `tavily_search` | Permits web queries; denies unauthorized tools |
| Memory Agent | `memory_search` | Permits vector queries; denies all other tools |
| Executor | None (Default) | Denies MCP tools unless extended by an active plugin |
| Verifier | None | Raises `ToolDenied` on any tool call attempt |

Plugins extend agent permissions by defining the optional `get_tool_permissions(agent_name)` method on `BaseWorkflowPlugin`. Tool calls are authorized at execution time in `mcp/client.py`, `api/mcp.py`, and `tools/search.py` via `harness.authorize(agent_name, tool_name)`.

### Limit Violation Lifecycle

When any threshold is crossed, the harness raises `BudgetExceeded(reason_code)`:
1. **Task Failure**: The task status in the database transitions to `failed`.
2. **Failure Persistence**: The reason code (`max_steps`, `max_seconds`, `max_cost_usd`, or `max_tokens`) along with a full resource snapshot (`step_count`, `elapsed_seconds`, `cost_total`, `token_total`, and limits) is stored as a JSON string in `tasks.failure_reason`.
3. **Manager Audit**: A `manager_decision` log entry documents the failure reason and resource consumption.
4. **SSE Broadcast**: A final SSE stream event is pushed to connected clients with `harness` data and the failure reason.
5. **Clean Termination**: Graph execution stops immediately without dangling subprocesses.

---

## Vector Memory System

AgentForge maintains long-term cross-task memory using dense vector similarity search, standardizing on 768-dimensional embeddings throughout the system.

### Dimensional Standardization
- **Embedding Model**: Google `gemini-embedding-001` invoked with `output_dimensionality=768`.
- **Normalization**: Every generated vector is L2-normalized before persistence or similarity calculation:
  `vector = vector / ||vector||_2`
- **Database Column**: Stored in a PostgreSQL `Vector(768)` column when running on PostgreSQL, or as a JSON-serialized array in SQLite.
- **Indexing**: PostgreSQL maintains an HNSW index configured for cosine distance:
  `CREATE INDEX ix_memories_embedding_hnsw ON memories USING hnsw (embedding vector_cosine_ops)`

### Retrieval and Priming
1. When the Memory Agent runs, it embeds the current user prompt into a 768-dimensional vector and L2-normalizes it.
2. It calculates the cosine similarity against all stored memory vectors.
3. Records scoring above 0.45 are ranked, and the top five historical solutions are injected into the Executor's priming context.
4. If no vector exists (legacy records), a lexical keyword matching fallback scores records based on query term frequency.

### Embedding Vector Reuse
The normalized query embedding computed during the initial retrieval phase is cached in `AgentState.prompt_embedding`. When the task completes and the deliverable is verified, the orchestrator invokes `MemoryAgent.store_memory`, passing the cached vector directly. This eliminates a redundant embedding API call at task completion.

### HNSW Filter Behavior
pgvector's HNSW index applies category and user filters *after* candidate selection from the index. Highly selective filters (e.g. rare category or per-user scope) can return fewer than `k` results. Mitigations:
- pgvector >= 0.8: `SET hnsw.iterative_scan = relaxed_order` for iterative indexed scans
- Increase candidate pool: set `HNSW_EF_SEARCH` environment variable (default: pgvector default of 40)

### PostgreSQL Migration Utility
`backend/scripts/migrate_to_postgres.py` transfers existing SQLite data to PostgreSQL:
- Verifies database connectivity and initializes pgvector.
- Creates tables in strict foreign-key dependency order.
- Detects legacy 3072-dimensional memory records and automatically re-embeds them using the 768-dimensional model before insertion.
- Builds the HNSW cosine index.

---

## Model Context Protocol Integration

AgentForge implements Anthropic's Model Context Protocol (MCP) standard (version 2024-11-05), enabling agents to interact with external tools and data sources via JSON-RPC 2.0.

### Protocol Sequence Diagram

```
AgentForge Client                              MCP Server Subprocess
       |                                                |
       |--- 1. stdio initialize (protocolVersion) ------>|
       |<-- 2. { result: serverCapabilities } ----------|
       |                                                |
       |--- 3. notifications/initialized -------------->|
       |                                                |
       |--- 4. tools/list ----------------------------->|
       |<-- 5. { result: { tools: [...] } } ------------|
       |                                                |
       |    [Runtime Harness Permission Check]          |
       |    harness.authorize(agent_name, tool_name)    |
       |                                                |
       |--- 6. tools/call { name, arguments } --------->|
       |<-- 7. { result: { content: [...] } } ----------|
```

### Security Architecture and RCE Elimination

To eliminate remote code execution risks and protect resource-constrained deployments (512 MB RAM), MCP server execution is governed by six strict security controls:

1. **Pre-Vetted Catalog Enablement**: Arbitrary command registration is disabled by default (`MCP_ALLOW_DYNAMIC_REGISTRATION=false`). Servers are enabled strictly through the pre-vetted catalog defined in `backend/config/mcp_catalog.json`. Each entry defines a fixed binary executable, pinned package version, network requirements, and strict parameter regex validation schemas. User input is never placed in executable or arbitrary argument positions.
2. **Subprocess Hardening Choke Point**: Process execution in `backend/app/mcp/client.py` uses direct positional arguments via `asyncio.create_subprocess_exec` rather than shell strings. Commands are validated against an exact-match allowlist (`MCP_ALLOWED_COMMANDS`). Inline evaluation flags (`-c`, `-e`, `--eval`, `-r`, `--import`) and shell metacharacters are rejected.
3. **Environment Isolation**: Child processes execute with a minimal scrubbed environment containing only system `PATH` and temporary directories. Sensitive parent environment variables (`GEMINI_API_KEY`, `TAVILY_API_KEY`, `DATABASE_URL`, `API_SECRET_KEY`, `ADMIN_API_KEY`) are stripped.
4. **Resource Quotas and Process Groups**: On POSIX runtimes, child processes are sandboxed via `setrlimit` (`RLIMIT_AS` capped at 256 MB, `RLIMIT_CPU` at 60s, `RLIMIT_NOFILE` at 128, `RLIMIT_NPROC` at 16). Subprocesses run in dedicated sessions (`os.setsid`) and are terminated across the entire process group upon timeout or shutdown.
5. **Administrative Separation and Auditability**: Server enablement, modification, and deletion require the `X-Admin-Key` header verified against `ADMIN_API_KEY` via `hmac.compare_digest`. When unset, administrative endpoints fail closed with HTTP 403. Every administrative action is logged to the `audit_logs` table with a 16-character SHA-256 hash of the actor key (never the raw key).
6. **SSRF Prevention for Remote SSE**: Remote MCP SSE endpoints must use `https://` and adhere to `MCP_ALLOWED_SSE_HOSTS`. Hostnames are resolved via DNS, and private, loopback, link-local, and cloud metadata (`169.254.169.254`) IP addresses are rejected with DNS rebinding protection and disabled redirects.

### Manual Verification Commands

The following curl commands verify MCP security controls against an active server deployment:

```bash
# 1. Attempt arbitrary command execution (expect 403 Forbidden or 422 Unprocessable Entity)
curl -s -X POST http://localhost:8000/api/mcp/servers \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your_admin_api_key" \
  -d '{"name": "evil", "command": "python", "args": ["-c", "import os; os.system(\"id\")"]}'

# 2. Attempt administrative access without admin key (expect 403 Forbidden)
curl -s -X POST http://localhost:8000/api/mcp/servers \
  -H "Content-Type: application/json" \
  -d '{"catalog_id": "fetch_service"}'

# 3. Enable safe catalog server with valid admin key (expect 200 OK)
curl -s -X POST http://localhost:8000/api/mcp/servers \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your_admin_api_key" \
  -d '{"catalog_id": "fetch_service"}'

# 4. Attempt unauthenticated task request when API_SECRET_KEY is configured (expect 401 Unauthorized)
curl -s -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Audit verification query", "plugin_name": "general_analysis"}'
```

---

## Workflow Plugin Engine

The plugin engine applies domain-specific operational presets to the agent workforce at task initialization.

### BaseWorkflowPlugin Interface
Every plugin extends `BaseWorkflowPlugin`, providing:
- `plugin_id`: Unique string key for identification.
- `name`: Human-readable display label.
- `description`: Detailed summary of capabilities.
- `get_custom_system_instruction(agent_name)`: Returns role persona overrides.
- `get_default_subtasks(prompt)`: Returns a recommended subtask decomposition.
- `get_tool_permissions(agent_name)`: Returns additional allowed tools for specific agents.

### Built-in Workflow Presets

| Plugin Identifier | Name | Targeted Capabilities | Agent Specializations |
|---|---|---|---|
| `startup_research` | Startup Market Research | Venture analysis, TAM/SAM/SOM sizing, SWOT analysis, competitor matrices | Planner: VC Principal<br>Analyst: BI Analyst<br>Executor: Venture Writer<br>Verifier: Due Diligence QA |
| `software_debug` | Software Debugging Suite | Root-cause analysis, 5-Whys diagnosis, SOLID remediation, unit testing | Planner: Systems Architect<br>Analyst: Root-Cause Analyst<br>Executor: Senior Engineer<br>Verifier: Code QA |
| `code_review` | Code Review Suite | Architectural critique, security audit, code smell identification | Specialized security and quality personas |
| `document_qa` | Document QA | Technical documentation analysis, synthesis, citation verification | Deep-dive research personas |
| `general_analysis` | General Analysis | Broad analytical synthesis, research summaries | Generalist analytical roles |

---

## Token Budget Engine

The token budget engine dynamically manages the `max_output_tokens` parameter for each LLM call to optimize performance and prevent token overruns.

### Tier Classification Matrix
Subtasks are classified into one of four tiers based on keyword semantics and accumulated prior context:

| Tier | Semantic Keywords | Context Promotion Threshold |
|---|---|---|
| SMALL | list, brief, quick, define, one-liner | Default for concise queries |
| MEDIUM | function, class, script, debug, fix, summarize, compare | Default for code snippets and summaries |
| LARGE | research, implement, build, create, report, guide, detailed | Promoted if prior context > 1,500 words |
| XL | comprehensive, investment memo, system design, white paper | Promoted if prior context > 3,000 words |

### Per-Agent Token Allocation Ceilings

| Agent Role | SMALL Tier | MEDIUM Tier | LARGE Tier | XL Tier |
|---|---|---|---|---|
| Executor | 1,500 tokens | 3,000 tokens | 6,000 tokens | 10,000 tokens |
| Researcher | 2,000 tokens | 4,000 tokens | 7,000 tokens | 10,000 tokens |
| Reasoner | 1,200 tokens | 2,500 tokens | 5,000 tokens | 8,000 tokens |
| Verifier | 1,000 tokens | 1,500 tokens | 2,000 tokens | 2,500 tokens |

The Verifier operates under compact ceilings because its structured JSON evaluation format requires minimal generation space. The Executor receives the highest ceiling to accommodate full deliverable production.

---

## Telemetry, Observability, and Pricing

AgentForge provides two layers of telemetry: local database tracking and optional distributed tracing via LangSmith.

### Local Telemetry Capture
Every LLM call records metrics directly to the `agent_logs` table:
- `prompt_tokens`: Input tokens from Gemini `usage_metadata`.
- `completion_tokens`: Output tokens generated.
- `total_tokens`: Total token consumption.
- `latency_ms`: Wall-clock execution time measured via `time.perf_counter`.
- `cost_usd`: Dollar cost calculated from dynamic pricing tables.

At task completion, the Manager aggregates these values into the task record (`total_tokens`, `total_cost_usd`, `total_latency_ms`).

### Dynamic Model Pricing
Pricing rates are loaded from `backend/config/model_prices.json` via a Pydantic schema in `core/telemetry.py`. If an unrecognized model is referenced, the system raises an explicit configuration error rather than falling back to arbitrary default rates.

### LangSmith Distributed Tracing
When `LANGSMITH_TRACING=true` and a valid `LANGSMITH_API_KEY` is provided, the `agent_traceable` decorator activates:
- Captures full LangGraph execution trees from Planner to Verifier.
- Logs prompts, token counts, schema definitions, and model outputs under the configured project namespace.
- Supports batch evaluation trace groupings.

---

## LLM-as-Judge Evaluation Framework

The platform includes an automated evaluation suite to benchmark deliverable quality against standardized test cases.

```
                    +------------------------------------+
                    |         Evaluation Runner          |
                    +------------------------------------+
                                      |
                         For each benchmark case:
                                      |
                                      v
                    +------------------------------------+
                    |       Analyst: Web Research        |
                    +------------------------------------+
                                      |
                                      v
                    +------------------------------------+
                    |       Executor: Build Result       |
                    +------------------------------------+
                                      |
                                      v
                    +------------------------------------+
                    |         LLMJudgeEvaluator          |
                    |         (Gemini 2.5 Flash)         |
                    |  Scores output across 5 dimensions |
                    +------------------------------------+
                                      |
                                      v
                    +------------------------------------+
                    |      Export Audit Reports          |
                    |  - eval_results/latest_report.json |
                    |  - eval_results/latest_report.md   |
                    +------------------------------------+
```

### Evaluation Rubric Dimensions

| Criterion | Weight | Evaluation Focus |
|---|---|---|
| Faithfulness | 25% | Absence of hallucinations; claims grounded in retrieved context |
| Answer Relevance | 25% | Direct satisfaction of core prompt objectives without padding |
| Completeness | 20% | Coverage of edge cases, constraints, and required sections |
| Technical Quality | 20% | Code correctness, type hints, SOLID structure, or analytical depth |
| Format Compliance | 10% | Markdown formatting, syntax highlighting, and table structures |

A benchmark case passes when the composite weighted score is >= 0.80 and both faithfulness and relevance are >= 0.70.

---

## Security Architecture

### Authentication Modes
- **Open Access Mode**: Enabled when `API_SECRET_KEY` is empty. Suitable for local development.
- **Locked Mode**: Enabled when `API_SECRET_KEY` is set. Protected endpoints require the key via `X-API-Key` or `Authorization: Bearer <token>`. Unauthorized requests receive HTTP 401. The `/health` endpoint remains public.

### Production CORS Policy
- Allowed origins are configured via `ALLOWED_ORIGINS` (default: `http://localhost:3000`).
- If `ENVIRONMENT="production"`, the application verifies that `ALLOWED_ORIGINS` is non-empty and does not contain wildcard `*` entries. The application refuses to start if these criteria are violated.

### Sliding Window Rate Limiting
- Managed by `RateLimiter` and `RateLimitMiddleware` in `core/rate_limiter.py`.
- Tracks request frequency per client identifier (hashed API key or client IP) across a rolling 60-second window.
- Configured via `RATE_LIMIT_ENABLED=true` and `RATE_LIMIT_PER_MINUTE=60`.
- Requests exceeding the threshold receive HTTP 429 with a `Retry-After` header.

---

## Database Architecture and Migration

AgentForge supports dual database configurations:
- **Production**: PostgreSQL 15+ with the `pgvector` extension.
- **Development**: SQLite with JSON-serialized vector arrays.

### Running with PostgreSQL via Docker
```bash
docker compose up -d postgres
```

### Migrating SQLite Data to PostgreSQL
The automated migration utility converts SQLite databases to PostgreSQL, re-embedding legacy vectors:
```bash
export DATABASE_URL=postgresql://agentforge:agentforge_password@localhost:5432/agentforge
python -m backend.scripts.migrate_to_postgres --source sqlite:///./agentforge.db
```

The script:
1. Validates connection parameters.
2. Initializes the PostgreSQL `vector` extension.
3. Builds tables in foreign-key dependency order.
4. Detects and re-embeds legacy 3072-dimensional records into 768-dimensional vectors.
5. Builds the HNSW index `ix_memories_embedding_hnsw`.

---

## Database Schema

### `tasks` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | String UUID | Primary Key | Unique task identifier |
| `prompt` | Text | Not Null | Original user objective |
| `status` | String | Not Null | pending, awaiting_plan_approval, running, awaiting_steering, completed, failed, cancelled |
| `plugin_name` | String | Nullable | Active workflow plugin identifier |
| `final_result` | Text | Nullable | Verified output deliverable |
| `failure_reason` | Text | Nullable | JSON snapshot of reason code and limits on budget failure |
| `total_tokens` | Integer | Default: 0 | Cumulative token consumption |
| `total_cost_usd` | Float | Default: 0.0 | Cumulative dollar expenditure |
| `total_latency_ms` | Float | Default: 0.0 | Cumulative execution time |
| `created_at` | DateTime | Default: UTC now | Creation timestamp |
| `updated_at` | DateTime | Default: UTC now | Last update timestamp |

### `subtasks` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | String UUID | Primary Key | Unique subtask identifier |
| `task_id` | String UUID | Foreign Key (tasks.id, Cascade) | Parent task identifier |
| `title` | String | Not Null | Subtask summary title |
| `description` | Text | Not Null | Detailed execution instruction |
| `assigned_agent` | String | Not Null | Designated agent role |
| `status` | String | Default: pending | pending, running, completed, failed |
| `output` | Text | Nullable | Output generated by assigned agent |
| `confidence_score` | Float | Nullable | Verifier confidence score |
| `order_index` | Integer | Not Null | Position in pipeline order |
| `created_at` | DateTime | Default: UTC now | Creation timestamp |

### `agent_logs` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | Primary Key, Autoincrement | Unique log entry identifier |
| `task_id` | String UUID | Foreign Key (tasks.id, Cascade) | Associated task identifier |
| `subtask_id` | String UUID | Foreign Key (subtasks.id), Nullable | Associated subtask identifier |
| `agent_name` | String | Not Null | Emitting agent identifier |
| `log_type` | String | Not Null | thinking, tool_call, output, error, telemetry, manager_decision, steering |
| `content` | Text | Not Null | Log message content or diagnostic payload |
| `prompt_tokens` | Integer | Default: 0 | Input token count |
| `completion_tokens` | Integer | Default: 0 | Output token count |
| `total_tokens` | Integer | Default: 0 | Combined token count |
| `latency_ms` | Float | Default: 0.0 | Execution duration in milliseconds |
| `cost_usd` | Float | Default: 0.0 | Estimated dollar cost |
| `created_at` | DateTime | Default: UTC now | Creation timestamp |

### `memories` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | String UUID | Primary Key | Unique memory record identifier |
| `category` | String | Not Null | Category classification: factual, code, insight |
| `content` | Text | Not Null | Composite memory text (goal, feedback, deliverable excerpt) |
| `embedding_searchable_text` | Text / Vector(768) | Nullable | 768-dim L2-normalized vector embedding |
| `created_at` | DateTime | Default: UTC now | Creation timestamp |

### `mcp_servers` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | String UUID | Primary Key | Server configuration identifier |
| `name` | String | Unique, Not Null | Unique server name |
| `transport` | String | Default: stdio | Transport type: stdio or sse |
| `command` | String | Not Null | Executable binary name (e.g., npx, python) |
| `args` | String | Default: [] | JSON-encoded argument list |
| `url` | String | Nullable | Endpoint URL for SSE transport |
| `is_active` | Boolean | Default: True | Server enablement flag |

### `audit_logs` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | String UUID | Primary Key | Unique audit log identifier |
| `action` | String | Not Null | Operation executed: enable_server, register_server, delete_server |
| `target_id` | String | Not Null | Target server name or catalog identifier |
| `actor` | String | Not Null | 16-character SHA-256 hash of the admin key (never raw key) |
| `details` | Text | Nullable | Serialized JSON parameters or execution status |
| `created_at` | DateTime | Default: UTC now | Event timestamp |

---

## API Reference

All API routes are prefixed with `/api`. Protected routes require authentication when `API_SECRET_KEY` is configured.

### Task Management Endpoints
- `POST /api/tasks`: Create and launch a new autonomous task.
- `GET /api/tasks`: List tasks ordered by creation time descending.
- `GET /api/tasks/{task_id}`: Retrieve detailed task status, subtasks, and failure reason.
- `DELETE /api/tasks/{task_id}`: Delete a task and cascade-delete associated records.
- `POST /api/tasks/{task_id}/approve_plan`: Approve or submit edited subtasks at the Plan Approval gate.
- `POST /api/tasks/{task_id}/steer`: Submit operator steering guidance at the Steering gate.
- `POST /api/tasks/{task_id}/reject`: Cancel task execution and terminate active asyncio tasks.
- `GET /api/tasks/{task_id}/logs`: Retrieve all agent log records for a task.
- `GET /api/tasks/{task_id}/stream`: Connect to the Server-Sent Events (SSE) progress stream.

### Memory Endpoints
- `GET /api/memory`: Query semantic vector memories with optional category filtering.
- `POST /api/memory`: Manually store a memory record.
- `DELETE /api/memory/{memory_id}`: Delete a specific memory entry.

### Workforce and Plugin Endpoints
- `GET /api/agents`: Retrieve registered agent roles and descriptions.
- `GET /api/plugins`: Retrieve available workflow plugin presets.

### Model Context Protocol Endpoints
- `GET /api/mcp/servers`: List configured MCP server integrations.
- `POST /api/mcp/servers`: Register and initialize a new MCP server.
- `DELETE /api/mcp/servers/{server_id}`: Terminate and delete an MCP server.
- `GET /api/mcp/tools`: List discovered tools across all active MCP servers.
- `POST /api/mcp/tools/call`: Test or execute an individual MCP tool call.

### Evaluation Endpoints
- `GET /api/evals/benchmarks`: List benchmark dataset test cases.
- `POST /api/evals/run`: Trigger execution of the evaluation benchmark suite.
- `GET /api/evals/latest`: Retrieve the latest evaluation summary report.

### SSE Stream Protocol
The `GET /api/tasks/{task_id}/stream` endpoint emits newline-delimited JSON events:
- `task_id`: Task identifier.
- `status`: Current lifecycle state.
- `final_result`: Verified output text (populated upon completion).
- `subtasks`: Array of current subtask objects.
- `new_logs`: Incremental agent log entries emitted since previous push.
- `harness`: Resource snapshot object (`step_count`, `elapsed_seconds`, `cost_total`, `token_total`, and limits).
- `failure_reason`: Reason code and error details when budget is exceeded.
- Keepalive ping comments are dispatched every 15 seconds to maintain proxy connections.

---

## Frontend Architecture

The user interface is built on Next.js 16 with React 19, Tailwind CSS 4, and Framer Motion.

### Route Structure
- `/`: Task creation portal and plugin selection.
- `/chat`: Real-time execution console with live SSE streaming, graph visualizer, and HITL gate cards.
- `/agents`: Workforce directory displaying agent personas and status.
- `/memory`: Interactive vector memory browser and similarity inspector.
- `/mcp`: MCP server management interface and tool testing console.
- `/plugins`: Workflow plugin catalog and configuration viewer.
- `/recent`: Historical task directory with metrics and analytics.
- `/settings`: Application configuration and environment viewer.

### Core Interface Components
- `AgentTerminal`: Streaming Thinking Console displaying categorized, color-coded agent logs. Manager decisions appear with amber highlights, and telemetry metrics display latency and token counts.
- `WorkflowGraph`: Real-time SVG visualization of the LangGraph node execution topology with active state animations.
- `PlanEditorCard`: Human-in-the-loop plan review component supporting inline editing, reordering, subtask insertion/deletion, and timeout countdowns.
- `SteeringPanel`: Mid-execution intercept panel displaying Verifier scores and diagnostic findings with a steering instruction input.
- `Harness Usage Bar`: Progress indicators rendered in the chat header displaying step count, token consumption, and dollar expenditure against configured `RunLimits`. Displays alert banners upon limit violations.
- `MarkdownRenderer`: Deliverable renderer supporting syntax-highlighted code blocks, mathematical expressions, GitHub alerts, and structured tables.

---

## Performance Engineering

- **Unified Research Invocation**: Analyst Agent executes Tavily search and SWOT reasoning in a single LLM call, reducing pipeline duration by 6 seconds.
- **Query Embedding Caching**: The 768-dimensional vector generated during memory lookup is preserved in `AgentState.prompt_embedding` and reused at task completion, saving one embedding API call per task.
- **Concurrent Research Node**: The `parallel_research` node runs `memory_agent` and `analyst` simultaneously via `asyncio.gather`, reducing research latency by 35%.
- **Zero-Cost Supervisor**: Manager Agent logs all milestones directly to the database without AI model calls, preserving token budget for task work.
- **Input Truncation Safeguards**: Context aggregators truncate inputs exceeding 8,000 characters before prompt compilation, preventing context window saturation while retaining complete text in state.
- **Dedicated Thread Pool**: LLM calls run in a dedicated `ThreadPoolExecutor(max_workers=10)`, keeping FastAPI's primary async event loop unblocked.
- **Rate Limit Resilience**: BaseAgent intercepts HTTP 429 `RESOURCE_EXHAUSTED` responses, extracts server `retryDelay`, and applies exponential backoff with jitter across three attempts.

---

## Technology Stack

| Layer | Component | Version / Specification |
|---|---|---|
| Large Language Model | Google Gemini 2.5 Flash | Google GenAI SDK |
| Text Embedding Model | Google gemini-embedding-001 | 768 Dimensions, L2-Normalized |
| External Search Engine | Tavily Search API | REST Client |
| Backend Framework | FastAPI | 0.115+ |
| Graph Orchestration | LangGraph | 1.x StateGraph |
| Database ORM | SQLAlchemy | 2.0 (Async + Sync Engines) |
| Data Validation | Pydantic v2 | 2.x |
| Vector Storage | PostgreSQL + pgvector | 768-dim HNSW Cosine Index |
| Local Database | SQLite | Zero-Config Fallback |
| Tool Protocol | Model Context Protocol (MCP) | Specification 2024-11-05 |
| Observability | LangSmith | Distributed Tracing |
| Frontend Framework | Next.js | 16 (App Router) |
| UI Runtime | React | 19 |
| Styling | Tailwind CSS | 4 |
| Motion Engine | Framer Motion | 12 |
| Component Icons | Lucide React | 1.x |

---

## Repository Structure

```
agentforge/
|
+-- backend/
|   +-- app/
|   |   +-- agents/
|   |   |   +-- base.py                 BaseAgent handling execution, telemetry, and backoff
|   |   |   +-- manager_agent.py        Zero-cost supervisor recording database audit logs
|   |   |   +-- planner.py              Goal decomposition into Pydantic subtask plans
|   |   |   +-- analyst_agent.py        Unified live web research and SWOT reasoning
|   |   |   +-- executor.py             Deliverable builder with 8,000-char truncation
|   |   |   +-- verifier.py             Five-dimensional QA rubric scoring and URL sanitization
|   |   |   +-- memory_agent.py         768-dim L2-normalized cosine vector search and archive
|   |   |   +-- researcher.py           Standalone research agent for specialized plugins
|   |   |   +-- reasoner.py             Standalone critical reasoning agent
|   |   |   +-- token_budget.py         Four-tier dynamic token allocation engine
|   |   +-- api/
|   |   |   +-- tasks.py                Task CRUD, SSE streaming, and HITL gate endpoints
|   |   |   +-- agents.py               Agent workforce directory endpoint
|   |   |   +-- memory.py               Vector memory query and storage endpoints
|   |   |   +-- plugins.py              Workflow plugin registry endpoint
|   |   |   +-- mcp.py                  MCP server registration and tool execution
|   |   |   +-- evals.py                Benchmark listing, runner, and audit report endpoints
|   |   |   +-- export.py               Task report export utilities
|   |   +-- core/
|   |   |   +-- config.py               Pydantic configuration settings and environment loading
|   |   |   +-- security.py             API key verification and authentication dependencies
|   |   |   +-- telemetry.py            Dynamic pricing loader, metrics logging, LangSmith tracing
|   |   |   +-- rate_limiter.py         In-memory sliding window rate limiter middleware
|   |   |   +-- stream.py               Server-Sent Events connection and broadcast manager
|   |   +-- database/
|   |   |   +-- connection.py           Database engine setup, session factories, schema migration
|   |   |   +-- models.py               SQLAlchemy ORM models: Task, Subtask, AgentLog, Memory, MCPServer, AuditLog
|   |   +-- evals/
|   |   |   +-- datasets.py             Standardized benchmark test case definitions
|   |   |   +-- evaluator.py            LLMJudgeEvaluator with five-dimension scoring
|   |   |   +-- rubrics.py              Evaluation schemas and report models
|   |   |   +-- runner.py               Batch evaluation runner and report export
|   |   +-- harness/
|   |   |   +-- limits.py               RunLimits schema (steps, seconds, cost, tokens)
|   |   |   +-- permissions.py          Default least-privilege agent tool allowlists
|   |   |   +-- errors.py               BudgetExceeded and ToolDenied exception types
|   |   |   +-- harness.py              AgentHarness runtime monitor and authorization engine
|   |   +-- mcp/
|   |   |   +-- catalog.py              Pre-vetted catalog loader and parameter schema validation
|   |   |   +-- client.py               SingleMCPClient (stdio/sse) and MCPManager
|   |   |   +-- security.py             Subprocess hardening, flag denylist, and SSRF prevention
|   |   +-- plugins/
|   |   |   +-- base_plugin.py          Abstract BaseWorkflowPlugin interface
|   |   |   +-- registry.py             Plugin registration and discovery system
|   |   |   +-- startup_research.py     Startup Market Research plugin
|   |   |   +-- software_debug.py       Software Debugging Suite plugin
|   |   |   +-- code_review.py          Code Review plugin
|   |   |   +-- document_qa.py          Document QA plugin
|   |   |   +-- general_analysis.py     General Analysis plugin
|   |   +-- tools/
|   |   |   +-- search.py               Tavily web search tool with harness authorization
|   |   +-- workflows/
|   |   |   +-- state.py                AgentState TypedDict definition
|   |   |   +-- orchestrator.py         LangGraph StateGraph, routing logic, and runner
|   |   |   +-- gate_registry.py        Asynchronous event registry for HITL gates
|   |   |   +-- task_registry.py        Active asyncio.Task registry for task cancellation
|   |   +-- main.py                     FastAPI application factory, CORS, and lifespan events
|   +-- config/
|   |   +-- mcp_catalog.json            Pre-vetted catalog of lightweight MCP server definitions
|   |   +-- model_prices.json           Dynamic per-million token pricing for models
|   +-- eval_results/
|   |   +-- latest_eval_report.json     Machine-readable benchmark report
|   |   +-- latest_eval_report.md       Markdown-formatted evaluation summary
|   +-- scripts/
|   |   +-- migrate_to_postgres.py      SQLite to PostgreSQL migration with 768-dim re-embedding
|   +-- tests/
|   |   +-- conftest.py                 Pytest fixtures and test database configuration
|   |   +-- integration/
|   |   |   +-- test_api_tasks.py       Integration tests for API endpoints
|   |   +-- unit/
|   |       +-- test_mcp_security.py    MCP catalog, subprocess hardening, and admin key tests
|   |       +-- test_harness.py         Harness limits, permissions, and cancellation unit tests
|   |       +-- test_memory_agent.py    768-dim cosine similarity and normalization tests
|   |       +-- test_orchestrator_routing.py Routing logic and retry step counting tests
|   |       +-- test_hitl_timeout.py    GateRegistry event signaling and timeout tests
|   |       +-- test_telemetry.py       Dynamic pricing loader and cost computation tests
|   |       +-- test_security.py        API authentication and CORS production check tests
|   |       +-- test_token_budget.py    Token budget tier classification tests
|   |       +-- test_evals.py           Evaluation rubric and runner tests
|   +-- requirements.txt               Pinned Python dependencies
|   +-- Dockerfile                      Backend container configuration
|
+-- frontend/
|   +-- src/
|   |   +-- app/
|   |   |   +-- layout.tsx              Root layout and theme providers
|   |   |   +-- page.tsx                Landing and task creation page
|   |   |   +-- chat/page.tsx           Workspace with SSE console and harness usage bar
|   |   |   +-- agents/page.tsx         Workforce directory page
|   |   |   +-- memory/page.tsx         Vector memory browser
|   |   |   +-- mcp/page.tsx            MCP server and tool management page
|   |   |   +-- plugins/page.tsx        Workflow plugin catalog
|   |   |   +-- recent/page.tsx         Historical task directory and metrics
|   |   |   +-- settings/page.tsx       System configuration settings page
|   |   +-- components/
|   |   |   +-- AgentTerminal.tsx       Streaming Thinking Console
|   |   |   +-- WorkflowGraph.tsx       Real-time SVG LangGraph visualizer
|   |   |   +-- PlanEditorCard.tsx      HITL Plan Approval review component
|   |   |   +-- SteeringPanel.tsx       HITL Steering intercept component
|   |   |   +-- AgentCard.tsx           Agent persona status card
|   |   |   +-- Timeline.tsx            Execution step timeline
|   |   |   +-- MarkdownRenderer.tsx    Markdown deliverable renderer
|   |   |   +-- Sidebar.tsx             Primary navigation sidebar
|   |   |   +-- DeleteConfirmModal.tsx  Confirmation dialog for deletions
|   |   +-- lib/
|   |       +-- api.ts                  Type definitions and typed REST/SSE client
|   +-- package.json                    Frontend dependencies and build scripts
|   +-- Dockerfile                      Multi-stage frontend container configuration
|
+-- .env.example                        Environment variable template
+-- docker-compose.yml                  Container orchestration configuration
+-- render.yaml                         Render cloud deployment configuration
+-- README.md                           Comprehensive technical documentation
```

---

## Configuration Reference

All settings are configured via environment variables. Create a `.env` file in the project root based on `.env.example`.

| Variable | Default Value | Description |
|---|---|---|
| `GEMINI_API_KEY` | Required | Google AI Studio API key for Gemini 2.5 Flash and embeddings |
| `TAVILY_API_KEY` | Required | Tavily API key for Analyst live web research |
| `DATABASE_URL` | `sqlite:///./agentforge.db` | SQLAlchemy connection URL (SQLite or PostgreSQL) |
| `ENVIRONMENT` | `development` | Deployment environment: `development`, `staging`, or `production` |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated list of allowed CORS origins |
| `API_SECRET_KEY` | None | Secret key required for API access when locked mode is active |
| `ADMIN_API_KEY` | None | Secret key required for MCP server management (fails closed when unset) |
| `HITL_TIMEOUT_SECONDS` | `60.0` | Timeout in seconds before HITL gates auto-proceed |
| `HARNESS_MAX_STEPS` | `25` | Maximum total graph execution steps allowed per task |
| `HARNESS_MAX_SECONDS` | `300.0` | Maximum active execution duration in seconds per task (excluding HITL pauses) |
| `HARNESS_MAX_PAUSED_SECONDS` | None | Optional maximum cumulative paused duration in seconds across HITL gates |
| `HARNESS_MAX_COST_USD` | `0.50` | Maximum cumulative dollar expenditure allowed per task |
| `HARNESS_MAX_TOKENS` | `120000` | Maximum cumulative token consumption allowed per task |
| `RATE_LIMIT_ENABLED` | `true` | Enables sliding window rate limiting |
| `RATE_LIMIT_PER_MINUTE` | `60` | Maximum allowed requests per minute per client |
| `MCP_SERVERS_JSON` | `[]` | JSON array of MCP server configuration objects loaded at launch |
| `MCP_ALLOWED_COMMANDS` | `npx,node,python` | Comma-separated allowlist of permitted binary names for MCP processes |
| `MCP_ALLOW_DYNAMIC_REGISTRATION` | `false` | When false, only pre-vetted catalog entries may be enabled |
| `MCP_ALLOWED_SSE_HOSTS` | Empty | Comma-separated allowlist of permitted hostnames for remote SSE MCP servers |
| `LANGSMITH_TRACING` | `false` | Enables LangSmith distributed tracing |
| `LANGSMITH_API_KEY` | None | API key for LangSmith tracing platform |
| `LANGSMITH_PROJECT` | `AgentForge` | Project identifier for LangSmith trace groupings |
| `LANGSMITH_ENDPOINT` | `https://api.smith.langchain.com` | LangSmith API endpoint |
| `HOST` | `0.0.0.0` | Backend host bind address |
| `PORT` | `8000` | Backend port |

---

## Local Development and Operations

### Prerequisites
- Python 3.11+
- Node.js 20+
- Google Gemini API key
- Tavily Search API key

### Backend Installation and Startup
```bash
# Initialize virtual environment
python -m venv backend/venv

# Activate virtual environment
# Windows:
backend\venv\Scripts\activate
# macOS / Linux:
source backend/venv/bin/activate

# Install pinned dependencies
pip install -r backend/requirements.txt

# Start backend service
python -m backend.app.main
```
The REST API is served at `http://localhost:8000`. Interactive documentation is available at `http://localhost:8000/docs`.

### Frontend Installation and Startup
```bash
cd frontend
npm install
npm run dev
```
The web interface is served at `http://localhost:3000`.

### Container Orchestration
To start both backend and frontend services with a local PostgreSQL container:
```bash
docker compose up --build
```

### Running Test Suites
```bash
# Run all unit tests
pytest backend/tests/unit/

# Run API integration tests
pytest backend/tests/integration/

# Run complete test suite
pytest backend/tests/
```

### Executing Evaluation Benchmarks
```bash
curl -X POST http://localhost:8000/api/evals/run \
  -H "Content-Type: application/json" \
  -d '{"category": "all"}'
```
Reports are written to `backend/eval_results/latest_eval_report.md` and `backend/eval_results/latest_eval_report.json`.

---

## License

Distributed under the MIT License. See `LICENSE` for details.
