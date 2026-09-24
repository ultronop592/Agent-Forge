# AgentForge

## Autonomous Multi-Agent Workforce Platform

AgentForge is a production-grade autonomous AI workforce system built for orchestrating coordinated teams of specialized agents that plan, research, execute, and verify complex tasks. Rather than relying on a single generalist prompt, AgentForge decomposes user goals into structured subtask pipelines, delegates each subtask to a role-appropriate specialist agent, and delivers fully verified deliverables with real-time progress streaming.

The platform is designed to operate in production environments with self-healing verification loops, human-in-the-loop control gates, cross-task vector memory, extensibility through the Model Context Protocol, and end-to-end telemetry observability.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Agent Workforce](#agent-workforce)
4. [Workflow State Machine](#workflow-state-machine)
5. [Human-in-the-Loop Control Gates](#human-in-the-loop-control-gates)
6. [Vector Memory System](#vector-memory-system)
7. [Model Context Protocol Integration](#model-context-protocol-integration)
8. [Workflow Plugin Engine](#workflow-plugin-engine)
9. [Token Budget Engine](#token-budget-engine)
10. [Telemetry and Observability](#telemetry-and-observability)
11. [LLM-as-Judge Evaluation Framework](#llm-as-judge-evaluation-framework)
12. [API Reference](#api-reference)
13. [Database Schema](#database-schema)
14. [Security Model](#security-model)
15. [Performance Engineering](#performance-engineering)
16. [Frontend Architecture](#frontend-architecture)
17. [Technology Stack](#technology-stack)
18. [Repository Structure](#repository-structure)
19. [Configuration Reference](#configuration-reference)
20. [Local Development Setup](#local-development-setup)
21. [Testing](#testing)
22. [Deployment](#deployment)

---

## System Overview

AgentForge solves the fundamental problem of AI reliability and coordination by structuring execution as a stateful, multi-agent pipeline rather than a single-shot generation request. Each agent in the workforce is a specialized role with a focused system instruction, its own token allocation strategy, and its own telemetry footprint.

The core design principles are:

**Deterministic Orchestration.** All agent routing is managed by a LangGraph StateGraph compiled at startup. The routing logic is pure, conditional, and testable in isolation. There is no implicit tool-calling or agent chaining that falls outside the graph.

**Self-Healing Quality Loops.** The Verifier agent evaluates every deliverable against a structured rubric. If the confidence score falls below 0.80, the pipeline routes back to the Executor with specific correction feedback. This loop repeats up to three times before the system escalates to the user.

**Zero-Overhead Supervision.** The Manager Agent coordinates the entire pipeline without making a single LLM call. All routing announcements, parallel dispatch logs, and final run summaries are written to the database as structured log entries at zero AI cost.

**Human Control Points.** Two gated pause points allow humans to inspect, modify, and approve the system's plan before and during execution. Both gates have configurable auto-proceed timeouts.

**Cross-Task Learning.** Every completed task is archived as a 3072-dimensional vector embedding in the memory store. Future tasks query this store using cosine similarity to surface relevant historical context before execution begins.

---

## Architecture

The following diagram illustrates the complete system architecture from request ingestion through delivery.

```
                     +-------------------------------------------------------+
                     |                   AGENTFORGE PLATFORM                 |
                     +-------------------------------------------------------+
                                               |
                 +-----------------------------+-----------------------------+
                 |                             |                             |
    +------------+------------+   +-----------+-----------+   +------------+------------+
    |    Next.js Frontend     |   |    FastAPI Backend     |   | PostgreSQL / SQLite     |
    |    (React 19, SSE)      |   |    (REST + SSE)        |   | (Task + Memory DB)      |
    +------------+------------+   +-----------+-----------+   +------------+------------+
                 |                             |                             |
                 |   POST /api/tasks           |                             |
                 |---------------------------->|                             |
                 |                             |   Write Task Record         |
                 |                             |---------------------------->|
                 |                             |                             |
                 |   GET /tasks/{id}/stream (SSE)                           |
                 |<----------------------------|                             |
                 |                             |                             |
                 |                             v                             |
                 |                  +----------+----------+                  |
                 |                  |  LangGraph          |                  |
                 |                  |  Orchestrator       |                  |
                 |                  |  StateGraph         |                  |
                 |                  +----------+----------+                  |
                 |                             |                             |
     +-----------+-----------+----------------+---+                          |
     |                       |                    |                          |
+----+--------+   +----------+--------+  +--------+-----------+             |
| Planner     |   | Parallel Research |  | Gemini 2.5 Flash   |             |
| Agent       |   | Memory + Analyst  |  | (LLM Provider)     |             |
| (Decompose) |   | asyncio.gather    |  |                    |             |
+-------------+   +----------+--------+  +--------------------+             |
                             |                                               |
              +--------------+----------------+                              |
              |       Executor Agent          |                              |
              |       (Deliverable Builder)   |                              |
              +--------------+----------------+                              |
                             |                                               |
                    +--------+--------+                                      |
                    |  Verifier Agent  |                                     |
                    |  (QA + Scoring)  |                                     |
                    +--------+--------+                                      |
                             |                                               |
               +-------------+-------------+                                 |
               |                           |                                 |
      is_valid = true              is_valid = false                          |
      retry_count >= 3             retry_count < 3                           |
               |                           |                                 |
    +----------+----------+     +----------+----------+                      |
    | Task Completed      |     | Self-Healing Loop   |                      |
    | Memory Archived     |     | Back to Executor    |                      |
    | SSE Final Event     |     | with Feedback       |                      |
    +---------------------+     +---------------------+                      |
```

---

## Agent Workforce

The AgentForge workforce consists of six purpose-built agents, each with a distinct role, specialized system instruction, and independent token budget configuration.

### Planner Agent

The entry point for every task. The Planner receives the user's raw goal and a plugin context, then generates a structured execution plan as a list of ordered subtasks. Each subtask specifies a title, description, and the assigned downstream agent. The plan is persisted to the database and surfaced in the frontend for human review before any execution begins.

The Planner uses Pydantic-validated structured output to guarantee that the plan schema is machine-parseable by the orchestrator.

### Manager Agent

The Manager operates as the zero-cost orchestration supervisor. It makes no LLM calls and consumes no API budget. Its responsibilities are limited to writing structured log entries that document every significant pipeline event: agent dispatch announcements, parallel stage activation, agent completion confirmations, HITL gate pauses, self-healing retry notifications, and final run summary reports.

All Manager log entries are tagged with log type "manager_decision" and appear in the Thinking Console under an amber highlight in the UI.

The Manager's run summary, written at task completion, aggregates total pipeline latency, total token consumption, total cost in USD, the sequence of agents that executed, and the final Verifier confidence score.

### Memory Agent

The Memory Agent maintains the platform's long-term institutional knowledge. On each task run, it performs a cosine similarity vector search against all previously completed task memories using a 3072-dimensional embedding generated by Google's gemini-embedding-001 model.

The agent returns the top-five semantically similar historical entries above a 45% similarity threshold. These entries are passed as contextual priming material to the Executor. After task completion, the Memory Agent archives the current task's outcome as a new memory record, reusing the cached embedding vector from the initial search to eliminate an extra API call.

If NumPy is available in the runtime environment, the cosine similarity computation uses optimized vectorized arithmetic. A pure Python fallback implementation handles environments without NumPy.

### Analyst Agent

The Analyst Agent performs live web research and critical reasoning in a single unified LLM call. It invokes the Tavily Search API to retrieve current information, then synthesizes the findings into a structured SWOT analysis and intelligence report.

Prior to this design, search and reasoning were split across two separate LLM calls. The unified approach eliminates one full API call from the pipeline and reduces latency by six or more seconds per task.

### Executor Agent

The Executor is the primary deliverable builder. It receives the aggregated output from all prior agents as context, combines it with the original goal and any Verifier correction feedback from previous retry attempts, and generates the final deliverable.

For large prior-agent contexts, the Executor applies a context truncation strategy. Contexts exceeding 8,000 characters are trimmed at a natural line boundary and annotated with a truncation notice. The full outputs remain available in the agent state for all downstream use.

### Verifier Agent

The Verifier is the final quality control stage. It evaluates the Executor's deliverable against the original goal across a structured rubric: faithfulness and absence of hallucinations, relevance to the goal, completeness, technical quality, and format compliance. The Verifier also applies a URL sanitization pass that identifies and strips fabricated or placeholder links from the output.

If the composite confidence score falls below 0.80, the Verifier marks the result as invalid, generates specific correction feedback, and the pipeline routes back to the Executor. If the score meets or exceeds the threshold, the deliverable is marked verified, archived to the memory store, and returned to the user.

---

## Workflow State Machine

The orchestrator is built on LangGraph's StateGraph, a directed acyclic graph with conditional routing. The full pipeline state is captured in a TypedDict called AgentState.

### State Fields

| Field | Type | Description |
|---|---|---|
| task_id | str | Unique identifier for the current task |
| prompt | str | The original user goal |
| plugin_name | str | The active workflow plugin identifier |
| subtasks | List | The ordered list of subtask records |
| current_subtask_index | int | Pointer to the current subtask being processed |
| agent_outputs | Dict | Map of subtask_id to agent output strings |
| verification_results | Dict | Verifier score, feedback, and validity flag |
| final_result | str | The verified, polished deliverable |
| retry_count | int | Number of Verifier-triggered self-healing retries |
| verifier_feedback | str | Feedback from the last verification pass |
| prompt_embedding | List[float] | Cached 3072-dim vector embedding for memory reuse |
| agent_sequence | List[str] | Ordered list of agents that executed, for run summary |
| manager_quality_scores | Dict | Per-subtask quality scores tracked by Manager |
| manager_skip_flags | Dict | Per-subtask skip flags for exhausted retries |
| agent_retry_counts | Dict | Per-subtask individual agent retry counters |

### Graph Topology

```
              Entry Point
                  |
          +-------+-------+
          |    planner    |
          +-------+-------+
                  |
          route_subtasks()
                  |
    +-------------+-------------+---------------+
    |             |             |               |
    v             v             v               v
parallel     memory_agent    analyst         executor
_research                                       |
    |             |             |               |
    +-------------+-------------+               |
                  |                             |
          route_subtasks() <-------------------+
                  |
                  | (all subtasks consumed)
                  v
            +-----+-----+
            |  verifier  |
            +-----+-----+
                  |
        route_verifier_output()
                  |
    +-------------+-------------+
    |                           |
    v                           v
executor                     __end__
(retry, count < 3)      (valid or max retries)
```

### Parallel Research Routing

When the router detects two or more consecutive research subtasks (assigned to memory_agent or analyst) at the current execution index, it routes to the parallel_research node instead of individual agent nodes. This node uses asyncio.gather to execute all qualifying research subtasks concurrently, then aggregates their outputs into the shared agent state before returning control to the router.

---

## Human-in-the-Loop Control Gates

Two explicitly designed pause points interrupt the autonomous pipeline and wait for human input before proceeding.

### Plan Approval Gate

After the Planner completes and the initial subtask plan is written to the database, the orchestrator transitions the task to status "awaiting_plan_approval" and pauses execution in a polling loop.

The frontend surfaces the full subtask plan in an interactive PlanEditorCard component. Users may:

- Edit subtask titles inline
- Reorder subtasks using directional controls
- Reassign subtasks to a different agent from a dropdown
- Add entirely new custom subtask steps
- Delete existing subtasks
- Approve the plan to resume execution
- Reject the plan to cancel the task entirely

The gate polls the task status every 500 milliseconds. If no user action is taken within the configurable timeout period (default 60 seconds), the gate auto-proceeds with the current plan and logs a timeout event.

When the user approves, the orchestrator re-fetches the subtask list from the database in order to capture any edits made during the review window before proceeding.

### Mid-Execution Steering Gate

When the Verifier marks a deliverable as invalid and a retry is required, the orchestrator transitions the task to status "awaiting_steering" before looping back to the Executor.

The frontend detects this status and renders a SteeringPanel component that displays the current Verifier confidence score, the specific findings that caused the failure, and a free-text input field for user-provided correction guidance.

Users may:

- Submit steering instructions to be injected into the next Executor prompt
- Force-accept the current deliverable as complete, bypassing further retry
- Cancel the task entirely

If no input is received within the timeout window, the gate auto-retries with the original Verifier feedback as the correction input.

---

## Vector Memory System

The memory system provides cross-task semantic recall using dense vector similarity search.

### Storage

Each completed task generates one memory record. The record stores:

- A rich content string combining the original goal, the Verifier's confidence rating and feedback, and a 350-character excerpt of the final deliverable.
- A category label derived from prompt keyword analysis: "code" for implementation tasks, "insight" for research and analysis tasks, and "factual" as the default.
- The 3072-dimensional embedding vector serialized as a JSON array in the embedding_searchable_text column.

Memory records are stored in the memories table in the same PostgreSQL or SQLite database used for task tracking.

### Retrieval

When the Memory Agent runs, it generates an embedding for the current task's search query, then computes cosine similarity against all stored memory vectors. Records scoring above the 45% threshold are sorted by score and the top five are returned.

If no vector is stored for a historical memory record (legacy records), the agent falls back to a keyword matching heuristic that scores based on the proportion of query words present in the memory content.

### Embedding Reuse

The query embedding computed during memory retrieval is cached in the AgentState under the prompt_embedding field. When the Verifier completes and the Verifier node stores the task outcome to memory, it passes this cached embedding directly to the store_memory method. This avoids a second embedding API call, which would otherwise cost an additional network round trip and API quota.

---

## Model Context Protocol Integration

AgentForge implements Anthropic's Model Context Protocol standard for connecting to external tool servers. This allows the agent workforce to invoke filesystem operations, database queries, web scrapers, code execution sandboxes, and any other capability exposed by a compliant MCP server.

### Communication Protocol

MCP servers communicate with the AgentForge engine over standard input and output using JSON-RPC 2.0 messages. Each message is a newline-delimited JSON object.

The handshake sequence follows the MCP 2024-11-05 protocol version specification:

```
AgentForge Client                      MCP Server
       |                                    |
       |--- initialize (protocolVersion) -->|
       |<-- { result: serverCapabilities } -|
       |--- notifications/initialized ----->|
       |--- tools/list -------------------->|
       |<-- { tools: [...] } --------------|
       |                                    |
       |--- tools/call { name, args } ----->|
       |<-- { content: [...] } ------------|
```

All requests include a UUID-based request ID for response correlation. Requests time out after 30 seconds if no response is received.

### Server Lifecycle

MCP servers are registered and started in two ways:

- From the database at application startup, where the MCPServer table records the server name, transport type, launch command, and command arguments.
- From the MCP_SERVERS_JSON environment variable at startup, which accepts a JSON array of server configuration objects.

On application shutdown, the MCPManager sends termination signals to all registered server subprocesses and awaits their exit.

### Management Dashboard

The /mcp page in the frontend provides a management interface for registering, inspecting, and removing MCP server configurations. Server connection status, the list of available tools, and their input schemas are visible directly in the UI. Individual tool calls can be tested with custom JSON argument payloads.

---

## Workflow Plugin Engine

The plugin engine allows domain-specific workflow presets to be applied to the agent workforce at task creation time.

### Plugin Architecture

Every plugin is a Python class that extends BaseWorkflowPlugin, an abstract base class that defines four required interfaces:

- plugin_id: A string key used to identify the plugin in API payloads and database records.
- name: A human-readable display name shown in the UI.
- description: A summary of the plugin's purpose and deliverables.
- get_custom_system_instruction(agent_name): Returns an agent-specific system instruction override. When a plugin is active, each agent checks this method for its role and replaces its default instruction with the plugin-provided persona.
- get_default_subtasks(prompt): Returns a suggested default subtask list that the Planner may use as a starting configuration.

Plugins are registered in the PluginRegistry at startup and are available through the /api/plugins endpoint.

### Built-in Plugins

**Startup Market Research Plugin**

This plugin transforms the entire workforce into a venture analysis team. The Planner adopts the role of a Venture Capital Principal, the Analyst becomes a Business Intelligence Analyst, the Executor becomes a Business Writer, and the Verifier becomes a Fact-Checking Specialist.

Default deliverables include competitor feature matrices, TAM/SAM/SOM market sizing tables, SWOT analyses, strategic risk registers, and investment thesis narratives.

**Software Debugging Suite Plugin**

This plugin reconfigures the workforce for software diagnostics and remediation. The Planner becomes a Principal Systems Architect, the Analyst becomes a Root-Cause Analyst, and the Executor becomes a Senior Software Engineer.

Default deliverables include detailed bug diagnostics, 5-Whys root cause explanations, SOLID-compliant code fixes, edge-case unit tests, and usage documentation.

---

## Token Budget Engine

The token budget engine dynamically selects the max_output_tokens parameter for each individual LLM call at runtime, preventing both token overruns on long-form tasks and unnecessary context allocation on simple requests.

### Tier Classification

The engine classifies each subtask into one of four tiers based on keyword matching against the combined subtask title and description. Classification proceeds from most-specific to most-general.

| Tier | Classification Examples |
|---|---|
| SMALL | "list", "brief", "quick", "what is", "define", "one-liner" |
| MEDIUM | "function", "class", "script", "debug", "fix", "summarize", "compare" |
| LARGE | "research", "implement", "build", "create", "report", "guide", "explain in detail" |
| XL | "comprehensive", "investment memo", "system design", "white paper", "competitive landscape", "due diligence" |

If the accumulated context from prior agents exceeds 1,500 words, the tier is promoted from MEDIUM to LARGE. If it exceeds 3,000 words, LARGE is promoted to XL. This ensures that later stages in the pipeline receive proportionally more generation headroom when prior agents have produced substantial content.

### Per-Agent Token Ceilings

Each agent type has independently tuned ceilings because their outputs have fundamentally different structural requirements.

| Agent | SMALL | MEDIUM | LARGE | XL |
|---|---|---|---|---|
| Executor | 1,500 | 3,000 | 6,000 | 10,000 |
| Researcher | 2,000 | 4,000 | 7,000 | 10,000 |
| Reasoner | 1,200 | 2,500 | 5,000 | 8,000 |
| Verifier | 1,000 | 1,500 | 2,000 | 2,500 |

The Verifier receives tighter ceilings because its structured JSON response schema does not require long prose. The Researcher receives higher minimum headroom because even small research tasks require citation formatting and section structure.

---

## Telemetry and Observability

AgentForge provides two complementary layers of observability: local database telemetry and optional distributed tracing via LangSmith.

### Local Telemetry

Every LLM call from every agent records the following metrics to the agent_logs table:

- prompt_tokens: Token count for the input prompt, extracted from Gemini's usage_metadata field.
- completion_tokens: Token count for the generated output.
- total_tokens: Sum of prompt and completion tokens.
- latency_ms: Wall-clock execution time in milliseconds measured with Python's time.perf_counter, providing microsecond-precision timing.
- cost_usd: Estimated dollar cost calculated from the token counts using the model's per-million-token pricing.

Additionally, a dedicated "telemetry" log entry is written for each call with a human-readable summary of these metrics, which appears in the frontend Thinking Console.

At task completion, the Manager Agent aggregates telemetry across all agent logs for that task and writes the totals to the Task record's total_tokens, total_cost_usd, and total_latency_ms columns. This enables the Recent Tasks view to display per-run cost and performance analytics without recomputing from logs.

### Model Pricing Reference

| Model | Input per 1M tokens | Output per 1M tokens |
|---|---|---|
| gemini-2.5-flash | $0.075 | $0.30 |
| gemini-1.5-flash | $0.075 | $0.30 |
| gemini-1.5-pro | $1.25 | $5.00 |
| gemini-embedding-001 | $0.025 | $0.00 |

### LangSmith Distributed Tracing

When a valid LANGSMITH_API_KEY is present and LANGSMITH_TRACING is set to true, AgentForge configures the LangSmith environment variables at startup and activates the agent_traceable decorator on all LLM call sites and the evaluation runner.

This enables:

- Full LangGraph execution trace visualization from Planner decomposition through verification completion.
- Per-LLM-call inspection including system prompts, token allocation, response schemas, and model outputs organized under project tags by agent name and task ID.
- Batch evaluation trace grouping under the AgentForge project namespace.

If LangSmith is not configured, the system operates in local telemetry mode with all metrics written to the database. No external network dependency is introduced in this mode.

---

## LLM-as-Judge Evaluation Framework

The evaluation framework provides a rigorous benchmarking system for measuring AgentForge's output quality across standardized test cases using a separate LLM judge instance.

### Evaluation Pipeline Architecture

```
  Evaluation Runner
        |
        |  For each benchmark case:
        |
  +-----+-------+
  | Analyst     |  Step A: Research and analyze the benchmark requirements
  +-----+-------+
        |
  +-----+-------+
  | Executor    |  Step B: Generate the deliverable
  +-----+-------+
        |
  +-----+-------------------+
  | LLMJudgeEvaluator       |  Step C: Grade the output across 5 rubric dimensions
  | (Gemini 2.5 Flash)      |
  +-----+-------------------+
        |
  +-----+-------------------+
  | EvalSummaryReport       |  Export JSON and Markdown to eval_results/ directory
  +-------------------------+
```

### Evaluation Rubric

Deliverables are scored on five criteria. Each criterion produces a score between 0.0 and 1.0 with an explanatory rationale string.

| Criterion | Weight | Measures |
|---|---|---|
| Faithfulness | 25% | Absence of hallucinations; all statements grounded in retrieved context |
| Answer Relevance | 25% | Direct alignment with the user's core intent; no evasive padding |
| Completeness | 20% | All constraints, edge cases, and required sections addressed |
| Technical Quality | 20% | Code correctness, type safety, SOLID compliance, or analytical rigor |
| Format Compliance | 10% | Clean markdown structure, tables, code blocks, and schema adherence |

The composite score is the weighted sum of the five criteria. A benchmark case passes if the composite score is at or above 0.80 and the faithfulness and relevance scores are each at or above 0.70.

### Benchmark Dataset

The standardized benchmark dataset includes test cases across three domains.

**Coding Benchmarks**

- Thread-Safe LRU Cache with TTL Eviction: O(1) get and put operations with thread-safe TTL expiration, edge cases, and SOLID design.
- Sliding Window Rate Limiter: Per-client request quota enforcement with timestamp tracking and graceful overflow handling.
- Async Database Connection Leak Fix: Root cause analysis and production-safe remedy for idle-in-transaction session leaks in SQLAlchemy async engines.

**Market and Strategic Research Benchmarks**

- AI Coding Assistant Market Intelligence: Competitor feature matrix, TAM/SAM/SOM sizing, SWOT analysis, and defensibility assessment across Cursor, Copilot, Windsurf, and Devin.
- Vector Database Comparison for Agentic RAG: Technical and TCO trade-off analysis across pgvector, Pinecone, and Qdrant for enterprise multi-agent retrieval workloads.

**Multi-Step Reasoning Benchmarks**

- SRE Incident Postmortem: Cascading microservices failure root cause, 5-Whys analysis, incident timeline, and preventive action items with SLI/SLA impact quantification.

### Audit Reports

Evaluation runs generate two output files saved to the eval_results directory:

- latest_eval_report.json: Machine-readable Pydantic model dump containing per-benchmark scores, latency, cost, and improvement suggestions.
- latest_eval_report.md: Human-readable markdown report with a criteria score breakdown table and per-case results.

The most recent report is accessible via the GET /api/evals/latest endpoint.

---

## API Reference

All API routes are prefixed with /api and require authentication if API_SECRET_KEY is configured. The health check endpoint at /health is always public.

### Tasks

| Method | Endpoint | Description |
|---|---|---|
| POST | /api/tasks | Create and launch a new task with a prompt and plugin selection |
| GET | /api/tasks | List all tasks ordered by creation time descending |
| GET | /api/tasks/{task_id} | Get task details including subtasks |
| DELETE | /api/tasks/{task_id} | Delete a task and all associated records |
| POST | /api/tasks/{task_id}/approve_plan | Approve (with optional edits) or pass through the execution plan |
| POST | /api/tasks/{task_id}/steer | Submit steering instructions during an awaiting_steering pause |
| POST | /api/tasks/{task_id}/reject | Cancel a task during any pause gate |
| GET | /api/tasks/{task_id}/logs | Retrieve all agent log entries for a task |
| GET | /api/tasks/{task_id}/stream | Open an SSE stream for real-time task progress |

### Memory

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/memory | Query the vector memory store with optional category filter |
| POST | /api/memory | Manually store a new memory record |
| DELETE | /api/memory/{memory_id} | Delete a specific memory record |

### Agents

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/agents | List all registered agents and their descriptions |

### Plugins

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/plugins | List all registered workflow plugins |

### MCP

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/mcp/servers | List all registered MCP server configurations |
| POST | /api/mcp/servers | Register and start a new MCP server |
| DELETE | /api/mcp/servers/{server_id} | Stop and remove a registered MCP server |
| GET | /api/mcp/tools | List all tools discovered from active MCP servers |
| POST | /api/mcp/tools/call | Invoke a specific tool on a named MCP server |

### Evaluations

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/evals/benchmarks | List available benchmark test cases with optional category filter |
| POST | /api/evals/run | Execute a benchmark evaluation run across the dataset |
| GET | /api/evals/latest | Retrieve the most recent evaluation summary report |

### SSE Stream Format

The task stream endpoint emits newline-delimited JSON payloads. Each payload includes:

- task_id: The task identifier
- status: The current task status
- final_result: The verified deliverable (populated at completion)
- subtasks: The current state of all subtask records
- new_logs: Any new agent log entries since the last emission

The stream also emits a ping comment every 15 seconds to prevent proxy idle connection timeouts. The stream terminates with a final done payload when the task reaches a terminal status.

---

## Database Schema

AgentForge uses SQLAlchemy ORM with support for Neon PostgreSQL in production and SQLite for local development. Schema migration is handled automatically via ensure_db_schema which adds missing columns on startup.

### Tasks Table

| Column | Type | Description |
|---|---|---|
| id | String UUID | Primary key |
| prompt | Text | The original user goal |
| status | String | pending, awaiting_plan_approval, running, awaiting_steering, completed, failed, cancelled |
| plugin_name | String | The active workflow plugin identifier |
| final_result | Text | The verified deliverable |
| total_tokens | Integer | Aggregated token count across all agent logs |
| total_cost_usd | Float | Aggregated estimated cost |
| total_latency_ms | Float | Aggregated execution time |
| created_at | DateTime | Record creation timestamp |
| updated_at | DateTime | Last modification timestamp |

### Subtasks Table

| Column | Type | Description |
|---|---|---|
| id | String UUID | Primary key |
| task_id | String FK | Foreign key to tasks, cascade delete |
| title | String | Short subtask title |
| description | Text | Detailed subtask description |
| assigned_agent | String | Agent responsible for this subtask |
| status | String | pending, running, completed, failed |
| output | Text | Agent output for this subtask |
| confidence_score | Float | Verifier confidence score |
| order_index | Integer | Execution order position |
| created_at | DateTime | Record creation timestamp |

### Agent Logs Table

| Column | Type | Description |
|---|---|---|
| id | Integer autoincrement | Primary key |
| task_id | String FK | Foreign key to tasks, cascade delete |
| subtask_id | String FK nullable | Optional foreign key to subtasks |
| agent_name | String | Name of the agent that produced this log |
| log_type | String | thinking, tool_call, output, error, telemetry, manager_decision, steering |
| content | Text | Log message or output content |
| prompt_tokens | Integer | Input token count |
| completion_tokens | Integer | Output token count |
| total_tokens | Integer | Total token count |
| latency_ms | Float | Execution time in milliseconds |
| cost_usd | Float | Estimated cost |
| created_at | DateTime | Record creation timestamp |

### Memories Table

| Column | Type | Description |
|---|---|---|
| id | String UUID | Primary key |
| category | String | factual, code, insight |
| content | Text | Rich memory content combining goal, feedback, and excerpt |
| embedding_searchable_text | Text | Serialized JSON array of the 3072-dim embedding vector |
| created_at | DateTime | Record creation timestamp |

### MCP Servers Table

| Column | Type | Description |
|---|---|---|
| id | String UUID | Primary key |
| name | String unique | Server display name |
| transport | String | stdio or sse |
| command | String | Launch command (e.g., npx, python) |
| args | String | JSON-serialized argument array |
| url | String nullable | URL for SSE transport mode |
| is_active | Boolean | Whether the server should be started at application launch |

---

## Security Model

API security is handled by the verify_api_key dependency injected into all API routes.

The security model has two operational modes:

**Open Access Mode.** When the API_SECRET_KEY environment variable is empty or unset, all requests are permitted without authentication. This mode is appropriate for local development and trusted internal deployments.

**Locked Mode.** When API_SECRET_KEY is set, all requests to protected routes must include the key either as an X-API-Key header or as a Bearer token in the Authorization header. Requests without a valid key receive a 401 Unauthorized response.

The health check endpoint at /health bypasses authentication in all modes.

CORS is configured to allow requests from origins specified by the ALLOWED_ORIGINS environment variable, which accepts a comma-separated list of allowed origin strings. The default value is a wildcard, which permits all origins.

---

## Performance Engineering

Several deliberate architectural decisions reduce API call count, latency, and operational cost.

### Unified Search and Reasoning

The AnalystAgent consolidates web research and SWOT reasoning into a single LLM invocation. Previously, these were two separate calls. The consolidation eliminates one API call per task and reduces pipeline latency by approximately six seconds under typical network conditions.

### Embedding Vector Reuse

The Memory Agent's query embedding, computed once for memory retrieval, is cached in the AgentState. When the Verifier stores the completed task to memory, it passes this cached vector directly. This eliminates one embedding API call at the end of every task.

### Zero-Cost Manager Coordination

The Manager Agent writes all its supervisory logs using database writes only. No LLM calls are made by the Manager under any circumstances, keeping the pipeline ceiling at five API calls per task under normal conditions.

### Parallel Research Stage

When the Planner schedules both the Memory Agent and Analyst Agent as consecutive subtasks (which is the default configuration), the orchestrator's routing logic detects this pattern and executes them simultaneously using asyncio.gather. This reduces research-phase wall-clock time by 30 to 40 percent compared to sequential execution.

### Large Output Safeguard

The Verifier agent applies a 6,000-character truncation to the Executor's output before including it in the verification prompt. This prevents the Verifier's context window from being exhausted by very large deliverables. The original, untruncated output is preserved in agent state and returned verbatim in the verified_output field regardless of the truncation applied during QA.

### SSE Heartbeat

The task stream endpoint emits a ping comment event every 15 seconds. This satisfies the keepalive requirements of common reverse proxies (including Render's infrastructure) that close idle connections after 55 seconds, ensuring reliable streaming across long-running tasks without the overhead of reconnection polling.

### Dedicated Thread Executor

All Gemini API calls are dispatched to a dedicated ThreadPoolExecutor with ten worker threads. This pool is separate from FastAPI's internal thread pool, preventing LLM API latency from blocking database writes and other synchronous I/O operations on the server.

### Rate Limit Handling

When the Gemini API returns a 429 RESOURCE_EXHAUSTED error, the BaseAgent parses the retryDelay value from the error message and waits the suggested interval plus a three-second buffer before retrying. This loop repeats up to three times per call before propagating the exception.

---

## Frontend Architecture

The frontend is a Next.js 16 application using the App Router and React 19. It connects to the backend via REST and SSE.

### Pages

| Route | Description |
|---|---|
| / | Landing page and task submission entry point |
| /chat | Main workspace with live SSE stream console |
| /agents | Agent workforce directory and status overview |
| /memory | Vector memory browser with similarity score display |
| /mcp | MCP server manager and tool inspector |
| /plugins | Workflow plugin selector |
| /recent | Task history, success rate analytics, and audit trail |

### Key Components

**AgentTerminal.** Renders the live streaming Thinking Console. Displays all agent log entries sorted by creation time with color-coded type labels. Manager Decision logs appear with amber highlight. Telemetry entries display token counts and cost. New entries animate in as SSE payloads arrive.

**WorkflowGraph.** Renders a live SVG visualization of the LangGraph node execution state. Active nodes are highlighted. Completed nodes show check marks. The graph updates as SSE payloads report subtask status changes.

**PlanEditorCard.** The human-in-the-loop Plan Approval gate component. Renders the subtask list with inline editing controls, reordering buttons, agent reassignment dropdowns, and approval and rejection actions. Includes a countdown timer showing seconds remaining before auto-proceed.

**SteeringPanel.** The mid-execution HITL intercept component. Displays the Verifier's confidence score and detailed findings. Provides a free-text input for correction instructions and buttons for force-accept and cancel actions.

**AgentCard.** Per-agent status display with role description, current execution state, and animated activity indicators.

**Timeline.** Chronological execution timeline visualization showing which agents have completed, which is active, and which are pending.

**MarkdownRenderer.** Renders the verified deliverable with full GitHub-style markdown support including syntax-highlighted code blocks, tables, blockquotes, and alert callouts.

**Sidebar.** Navigation sidebar with active route highlighting and agent status badges.

### State Management and API Client

The frontend does not use a dedicated state management library. All server state is managed through the SSE event stream in the chat workspace and through standard fetch calls with local component state for other views.

The lib/api.ts module centralizes all HTTP client calls and defines TypeScript interfaces matching the backend Pydantic schemas.

---

## Technology Stack

| Layer | Technology | Version |
|---|---|---|
| AI Model | Google Gemini 2.5 Flash | API |
| Embedding Model | Google gemini-embedding-001 | API |
| Search Engine | Tavily Search API | API |
| Backend Framework | FastAPI | 0.115+ |
| Workflow Orchestration | LangGraph | 1.x |
| Database ORM | SQLAlchemy | 2.0 |
| Schema Validation | Pydantic v2 | 2.x |
| HTTP Client | httpx | 0.28+ |
| Production Database | Neon PostgreSQL | Serverless |
| Local Database | SQLite | Built-in |
| Observability | LangSmith | 0.9+ |
| Frontend Framework | Next.js | 16 |
| UI Runtime | React | 19 |
| Animation | Framer Motion | 12 |
| Icons | Lucide React | 1.x |
| Styling | Tailwind CSS | 4 |
| Container Runtime | Docker | Latest |
| Backend Deployment | Render | Web Service |
| Frontend Deployment | Vercel | Serverless |

---

## Repository Structure

```
agentforge/
|
+-- backend/
|   +-- app/
|   |   +-- agents/
|   |   |   +-- base.py                 BaseAgent with LLM execution, telemetry, and retry logic
|   |   |   +-- manager_agent.py        Zero-cost orchestration supervisor
|   |   |   +-- planner.py              Goal decomposition into structured subtask plans
|   |   |   +-- analyst_agent.py        Unified web research and SWOT reasoning
|   |   |   +-- executor.py             Deliverable generation with context aggregation
|   |   |   +-- verifier.py             QA evaluation with URL sanitization and self-healing
|   |   |   +-- memory_agent.py         Cosine similarity vector search and memory archiving
|   |   |   +-- researcher.py           Standalone research agent for plugin use
|   |   |   +-- reasoner.py             Standalone reasoning agent for plugin use
|   |   |   +-- token_budget.py         Dynamic 4-tier token allocation engine
|   |   +-- api/
|   |   |   +-- tasks.py                Task CRUD, SSE streaming, HITL approval and steering
|   |   |   +-- agents.py               Agent directory endpoint
|   |   |   +-- memory.py               Memory query and storage endpoints
|   |   |   +-- plugins.py              Plugin registry endpoint
|   |   |   +-- mcp.py                  MCP server management and tool invocation
|   |   |   +-- evals.py                Benchmark listing, evaluation runner, and report retrieval
|   |   +-- core/
|   |   |   +-- config.py               Pydantic-settings configuration with env file loading
|   |   |   +-- security.py             X-API-Key and Bearer token verification
|   |   |   +-- telemetry.py            LangSmith setup, cost calculator, agent_traceable decorator
|   |   +-- database/
|   |   |   +-- connection.py           SQLAlchemy engine, session factory, schema migration
|   |   |   +-- models.py               Task, Subtask, AgentLog, Memory, MCPServer ORM models
|   |   +-- evals/
|   |   |   +-- datasets.py             Standardized benchmark test case definitions
|   |   |   +-- evaluator.py            LLMJudgeEvaluator with 5-dimensional scoring
|   |   |   +-- rubrics.py              Pydantic schemas for evaluation results and reports
|   |   |   +-- runner.py               Batch evaluation runner and report export
|   |   +-- mcp/
|   |   |   +-- client.py               SingleMCPClient (JSON-RPC stdio) and MCPManager
|   |   +-- plugins/
|   |   |   +-- base_plugin.py          Abstract BaseWorkflowPlugin interface
|   |   |   +-- registry.py             Plugin discovery and registration
|   |   |   +-- startup_research.py     Startup Market Research Plugin implementation
|   |   |   +-- software_debug.py       Software Debugging Suite Plugin implementation
|   |   +-- workflows/
|   |   |   +-- state.py                AgentState TypedDict definition
|   |   |   +-- orchestrator.py         LangGraph StateGraph with routing and all node implementations
|   |   +-- main.py                     FastAPI application factory, CORS, startup and shutdown lifecycle
|   +-- eval_results/
|   |   +-- latest_eval_report.json     Most recent benchmark evaluation machine-readable report
|   |   +-- latest_eval_report.md       Most recent benchmark evaluation human-readable report
|   +-- tests/
|   |   +-- conftest.py                 Pytest fixtures for test database and FastAPI test client
|   |   +-- integration/
|   |   |   +-- test_api_tasks.py       Integration tests for task, plugin, and agent endpoints
|   |   +-- unit/
|   |       +-- test_evals.py           Unit tests for evaluator, runner, and benchmark dataset
|   |       +-- test_hitl_timeout.py    Unit test for HITL timeout configuration
|   |       +-- test_memory_agent.py    Unit tests for cosine similarity implementation
|   |       +-- test_orchestrator_routing.py  Unit tests for routing functions
|   |       +-- test_security.py        Unit tests for API key verification logic
|   |       +-- test_telemetry.py       Unit tests for cost calculation and LangSmith setup
|   |       +-- test_token_budget.py    Unit tests for the token budget tier classification
|   +-- test_system.py                  Standalone manual smoke test for end-to-end integration
|   +-- Dockerfile                      Backend container image definition
|   +-- .dockerignore                   Docker build exclusion rules for backend
|   +-- requirements.txt               Python package dependencies
|
+-- frontend/
|   +-- src/
|   |   +-- app/
|   |   |   +-- layout.tsx              Root layout with global providers
|   |   |   +-- page.tsx                Landing page
|   |   |   +-- globals.css             Global styles and CSS custom properties
|   |   |   +-- chat/page.tsx           Main agent workspace with SSE console
|   |   |   +-- agents/page.tsx         Agent workforce directory
|   |   |   +-- memory/page.tsx         Vector memory browser
|   |   |   +-- mcp/page.tsx            MCP server and tool manager
|   |   |   +-- plugins/page.tsx        Workflow plugin selector
|   |   |   +-- recent/page.tsx         Task history and analytics
|   |   +-- components/
|   |   |   +-- AgentTerminal.tsx       Live streaming Thinking Console
|   |   |   +-- WorkflowGraph.tsx       Live SVG LangGraph visualizer
|   |   |   +-- PlanEditorCard.tsx      HITL plan review and editing gate
|   |   |   +-- SteeringPanel.tsx       Mid-execution steering intercept panel
|   |   |   +-- AgentCard.tsx           Per-agent status and role display
|   |   |   +-- Timeline.tsx            Execution timeline visualization
|   |   |   +-- MarkdownRenderer.tsx    Rich markdown output renderer
|   |   |   +-- Sidebar.tsx             Navigation sidebar
|   |   |   +-- DeleteConfirmModal.tsx  Confirmation modal for destructive actions
|   |   +-- lib/
|   |       +-- api.ts                  Typed REST client and TypeScript model interfaces
|   +-- public/
|   |   +-- .gitkeep                    Preserves the public assets directory
|   +-- Dockerfile                      Frontend container image definition (multi-stage)
|   +-- .dockerignore                   Docker build exclusion rules for frontend
|   +-- package.json                    Node.js dependencies and scripts
|   +-- next.config.ts                  Next.js configuration
|   +-- tsconfig.json                   TypeScript compiler configuration
|   +-- eslint.config.mjs               ESLint configuration
|   +-- postcss.config.mjs              PostCSS and Tailwind CSS configuration
|
+-- .env.example                        Template for all required environment variables
+-- .gitignore                          Git exclusion rules
+-- .dockerignore                       Root-level Docker build exclusion rules
+-- docker-compose.yml                  Local multi-service orchestration configuration
+-- render.yaml                         Render deployment configuration for backend
+-- README.md                           This document
```

---

## Configuration Reference

All configuration is managed through environment variables. Copy .env.example to .env and populate the required values before starting the application.

### Required Variables

| Variable | Description |
|---|---|
| GEMINI_API_KEY | Google AI Studio API key for Gemini 2.5 Flash and embedding model access |
| TAVILY_API_KEY | Tavily Search API key for the Analyst Agent's web research capability |
| DATABASE_URL | SQLAlchemy connection URL. Use sqlite:///./agentforge.db for local or a Neon PostgreSQL URL for production |

### Optional Variables

| Variable | Default | Description |
|---|---|---|
| HOST | 0.0.0.0 | Server bind address |
| PORT | 8000 | Server listen port |
| API_SECRET_KEY | empty | When set, all API requests require this key via X-API-Key header or Bearer token |
| ALLOWED_ORIGINS | * | Comma-separated list of allowed CORS origins |
| HITL_TIMEOUT_SECONDS | 60.0 | Seconds before HITL gates auto-proceed |
| MCP_SERVERS_JSON | [] | JSON array of MCP server configurations to load at startup |
| LANGSMITH_TRACING | false | Enable LangSmith distributed tracing |
| LANGSMITH_API_KEY | empty | LangSmith API key |
| LANGSMITH_PROJECT | AgentForge | LangSmith project name for trace grouping |
| LANGSMITH_ENDPOINT | https://api.smith.langchain.com | LangSmith API endpoint |

---

## Local Development Setup

### Prerequisites

- Python 3.11 or later
- Node.js 20 or later
- A Gemini API key obtained at aistudio.google.com
- A Tavily API key obtained at app.tavily.com

### Backend Setup

Create a virtual environment in the backend directory and install dependencies from the repository root:

    python -m venv backend/venv
    backend\venv\Scripts\activate          (Windows)
    source backend/venv/bin/activate       (macOS / Linux)
    pip install -r backend/requirements.txt

Copy the environment template and populate required values:

    cp .env.example .env

Start the backend server from the repository root:

    python -m backend.app.main

The API will be available at http://localhost:8000. Interactive documentation is available at http://localhost:8000/docs.

### Frontend Setup

Install Node.js dependencies and start the development server:

    cd frontend
    npm install
    npm run dev

The frontend will be available at http://localhost:3000.

### Docker Compose

To start both services together using Docker:

    docker-compose up --build

The backend will be accessible at http://localhost:8000 and the frontend at http://localhost:3000.

---

## Testing

The test suite uses pytest with pytest-asyncio for async test support. All tests use an isolated SQLite test database configured in the conftest.py fixtures.

### Running Unit Tests

Run all unit tests from the repository root:

    pytest backend/tests/unit/

### Running Integration Tests

Integration tests spin up a real FastAPI TestClient instance and execute HTTP requests against the full application stack:

    pytest backend/tests/integration/

### Running the Full Test Suite

    pytest backend/tests/

### Running the Evaluation Benchmark Suite

Trigger a full benchmark evaluation run via the REST API while the server is running:

    POST http://localhost:8000/api/evals/run
    Content-Type: application/json
    Body: {"category": "all"}

Evaluation results are saved automatically to backend/eval_results/latest_eval_report.md and backend/eval_results/latest_eval_report.json.

### Manual Smoke Test

A standalone integration smoke test can be run directly from the repository root:

    python backend/test_system.py

This script creates a test task in the database, invokes the full LangGraph orchestrator, and verifies that the database state reflects a completed run with subtasks and agent logs.

---

## Deployment

### Backend on Render

The render.yaml file in the repository root defines the backend service configuration for one-click deployment on Render using Docker.

Required environment variables to set in the Render dashboard:

- DATABASE_URL: Your Neon PostgreSQL connection string
- GEMINI_API_KEY: Your Gemini API key
- TAVILY_API_KEY: Your Tavily API key
- LANGSMITH_API_KEY: Your LangSmith API key (optional)
- API_SECRET_KEY: A secret key to lock down the API (optional but recommended for production)

The backend Dockerfile uses Python 3.11 slim as the base image, installs build-essential for compiled dependencies, and starts the application via the backend.app.main module entry point.

### Frontend on Vercel

Deploy the frontend to Vercel by connecting the repository and setting the root directory to frontend. Set the NEXT_PUBLIC_API_URL environment variable to the public URL of your deployed Render backend.

The frontend Dockerfile uses a multi-stage build. The builder stage compiles the Next.js production bundle. The runner stage copies only the compiled output into a minimal Node.js 20 Alpine image.

---

## License

MIT License. See LICENSE for details.
