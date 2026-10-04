# Project Structure Explained — Interview Guide

This document explains how every folder and file in AgentForge fits together.
Use this as your reference when explaining the project to an interviewer.

---

## The Big Picture — How to Explain It in 30 Seconds

"AgentForge is a full-stack AI platform I built from scratch.
The backend is a Python FastAPI server that runs a multi-agent pipeline using LangGraph.
The frontend is a Next.js dashboard that connects in real time using Server-Sent Events.
The whole system breaks a user's task into subtasks, runs them through specialized AI agents,
verifies the output, and streams everything live to the user."

---

## Top-Level Layout

```
agentforge/
|
+-- backend/          Everything on the server side — Python, AI agents, database
+-- frontend/         The web dashboard — Next.js, React
+-- docker-compose.yml  Runs both services together with one command
+-- render.yaml         Tells Render.com how to deploy the backend
+-- .env.example        Template showing what environment variables are needed
+-- .gitignore          Files Git should ignore (secrets, build folders, etc.)
+-- README.md           Full project documentation
```

**What to say:** "I separated the backend and frontend into their own folders.
Each one has its own Dockerfile so they can be deployed independently.
The docker-compose file lets me run both together locally."

---

## Backend Folder

```
backend/
|
+-- app/              The actual application code
+-- tests/            All test files
+-- eval_results/     AI benchmark reports generated at runtime
+-- test_system.py    A manual smoke test I can run to check everything works
+-- Dockerfile        How to build the backend as a Docker container
+-- requirements.txt  All Python packages the project needs
```

**What to say:** "The backend is split into the app logic, the tests, and some utility files.
requirements.txt is the Python equivalent of package.json in Node — it lists every dependency."

---

## The App Folder — The Heart of the Backend

```
backend/app/
|
+-- agents/       The six AI agents — each one has a specific job
+-- api/          The REST API routes — what URLs the server responds to
+-- core/         Shared utilities — configuration, security, telemetry
+-- database/     Database models and connection setup
+-- evals/        The LLM evaluation and benchmarking system
+-- mcp/          The Model Context Protocol client for external tools
+-- plugins/      Workflow presets that change agent behavior
+-- workflows/    The LangGraph state machine that orchestrates everything
+-- main.py       The entry point — starts the FastAPI server
```

**What to say:** "I organized the backend by responsibility.
Each folder has one clear job.
If an interviewer asks me to find where the API is defined, I go to api/.
If they ask about the database, I go to database/.
This makes the code easy to navigate and easy to test."

---

## Agents Folder — The Core AI Logic

```
backend/app/agents/
|
+-- base.py           The parent class every agent inherits from
+-- planner.py        Breaks the user's goal into a step-by-step plan
+-- manager_agent.py  Supervises the pipeline — no AI calls, zero cost
+-- memory_agent.py   Searches past task history using vector similarity
+-- analyst_agent.py  Does live web research and SWOT analysis in one step
+-- executor.py       Builds the final deliverable — the actual answer
+-- verifier.py       Checks the answer for quality, flags issues
+-- researcher.py     Used by workflow plugins for targeted research
+-- reasoner.py       Used by workflow plugins for deep reasoning
+-- token_budget.py   Decides how many tokens each agent call is allowed
```

**How to explain base.py:**
"base.py is the foundation. Every agent inherits from BaseAgent.
It handles the Gemini API call, measures how long it took (latency),
counts the tokens used, calculates the cost, and writes a log to the database.
So I only wrote that logic once — all six agents get it automatically through inheritance."

**How to explain token_budget.py:**
"This file solves a real problem. If you give every agent the same token limit,
small tasks waste money and big tasks get cut off.
So I built a keyword classifier. It reads the subtask description,
detects whether it is a small, medium, large, or XL task,
and picks the right token limit dynamically. Each agent type also has its own ceiling."

---

## API Folder — The REST Endpoints

```
backend/app/api/
|
+-- tasks.py    Create tasks, stream live updates, approve plans, steer execution
+-- memory.py   Query and store the vector memory bank
+-- agents.py   List the available agents
+-- plugins.py  List the available workflow plugins
+-- mcp.py      Manage external tool servers (MCP protocol)
+-- evals.py    Run AI benchmark evaluations and retrieve reports
```

**How to explain tasks.py:**
"tasks.py is the most important API file. It has the endpoint that creates a new task,
kicks off the AI pipeline in the background, and then streams real-time progress
to the frontend using Server-Sent Events.
It also has the approve_plan endpoint — that is the human-in-the-loop gate
where the user can edit the AI's plan before execution starts."

**Interview talking point on SSE:**
"I used Server-Sent Events instead of WebSockets because SSE is simpler and one-directional.
The server pushes updates to the client. I only needed server-to-client streaming,
so SSE was the right tool. I also added a heartbeat ping every 15 seconds
to stop the proxy from closing the connection during long-running tasks."

---

## Core Folder — Shared Utilities

```
backend/app/core/
|
+-- config.py      Reads all environment variables using Pydantic Settings
+-- security.py    Checks API keys on every request
+-- telemetry.py   Measures latency, counts tokens, calculates cost, connects LangSmith
```

**How to explain config.py:**
"I use Pydantic Settings to manage configuration.
It reads from the .env file and validates that required values like GEMINI_API_KEY are present.
This means if someone forgets to set an environment variable,
they get a clear error at startup instead of a confusing crash later."

**How to explain security.py:**
"The API has two modes. If you set the API_SECRET_KEY environment variable,
every request must include it as an X-API-Key header or Bearer token.
If you leave it empty, the API is open — useful for local development.
The health check endpoint is always public regardless."

**How to explain telemetry.py:**
"Every LLM call records three things: how long it took in milliseconds,
how many tokens were used, and the estimated dollar cost.
If LangSmith is configured, all of this also gets sent to LangSmith
for distributed tracing and visualization. If not, it stays local in the database."

---

## Database Folder

```
backend/app/database/
|
+-- connection.py    Sets up the SQLAlchemy engine, handles SQLite vs PostgreSQL
+-- models.py        Defines the database tables as Python classes
```

**How to explain models.py:**
"I have five database tables.
Tasks stores the main task record with its status and final result.
Subtasks stores each step in the plan with the assigned agent and output.
AgentLogs stores every log message from every agent — thinking, output, errors, telemetry.
Memories stores past task insights as vector embeddings for the memory system.
MCPServers stores external tool server configurations."

**How to explain connection.py:**
"The connection module detects whether DATABASE_URL points to SQLite or PostgreSQL
and configures the engine accordingly.
For PostgreSQL I set pool_pre_ping=True so the connection pool checks
if the connection is still alive before using it — this prevents the idle connection errors
that crash servers under load."

---

## Workflows Folder — The LangGraph Orchestrator

```
backend/app/workflows/
|
+-- state.py         Defines AgentState — the shared data structure all agents read and write
+-- orchestrator.py  The LangGraph graph — all the nodes, edges, and routing logic
```

**How to explain state.py:**
"AgentState is a TypedDict — essentially a typed dictionary that gets passed
through every step of the pipeline. Every agent reads what it needs from state
and writes its output back to state. This is how agents share information
without being directly coupled to each other."

**How to explain orchestrator.py:**
"This is where the LangGraph StateGraph lives. I define a node for each agent stage.
Then I add conditional edges with routing functions.
The route_subtasks function looks at the current subtask index and decides which agent to call next.
If two research subtasks are queued back to back, it routes to parallel_research
which runs both Memory Agent and Analyst Agent at the same time using asyncio.gather.
The route_verifier_output function decides whether to loop back to the Executor
or end the pipeline based on the Verifier's score."

---

## Evals Folder — AI Benchmarking

```
backend/app/evals/
|
+-- datasets.py     The test cases — 6 real-world prompts with expected quality criteria
+-- rubrics.py      The scoring schemas using Pydantic
+-- evaluator.py    The LLM judge that grades outputs across 5 dimensions
+-- runner.py       Runs all benchmarks and saves the report
```

**How to explain it:**
"This is an LLM-as-Judge evaluation system.
Instead of unit testing with fixed expected outputs — which does not work for AI —
I wrote benchmark prompts with golden criteria.
A separate Gemini instance acts as the judge and scores every output
on faithfulness, relevance, completeness, technical quality, and format.
The pass threshold is 80 percent composite score.
This lets me measure whether changes to the system improve or hurt output quality."

---

## MCP Folder — External Tool Protocol

```
backend/app/mcp/
|
+-- client.py    JSON-RPC client that talks to external MCP tool servers
```

**How to explain it:**
"MCP stands for Model Context Protocol — it is an open standard by Anthropic
for connecting AI systems to external tools like filesystems, databases, or APIs.
My client launches an external server as a subprocess,
does a JSON-RPC handshake over stdin and stdout,
discovers the available tools, and then routes tool call requests to the right server.
From the frontend, you can register any MCP-compatible server and call its tools directly."

---

## Plugins Folder — Workflow Presets

```
backend/app/plugins/
|
+-- base_plugin.py       The abstract interface all plugins must implement
+-- registry.py          Discovers and registers all plugins at startup
+-- startup_research.py  Startup market research preset
+-- software_debug.py    Software debugging preset
```

**How to explain it:**
"Plugins let me change the entire workforce's behavior without touching the core code.
Each plugin is a Python class that inherits from BaseWorkflowPlugin.
It defines what system instruction each agent gets — for example,
the Startup Research plugin makes the Planner act like a VC Principal
and the Executor act like a Business Writer.
This follows the Open-Closed Principle: I can add new plugins without modifying the orchestrator."

---

## Frontend Folder

```
frontend/
|
+-- src/
|   +-- app/          Pages — one folder per route
|   +-- components/   Reusable UI components
|   +-- lib/          API client and TypeScript types
+-- public/           Static files served directly
+-- package.json      Node.js dependencies
+-- next.config.ts    Next.js configuration
+-- Dockerfile        Multi-stage build for production deployment
```

**What to say:** "The frontend follows the Next.js App Router convention.
Each subfolder inside app/ maps to a URL route.
Components are the reusable pieces I assemble into pages.
lib/api.ts is the single file that handles all communication with the backend."

---

## Components Folder — Key UI Pieces

```
frontend/src/components/
|
+-- AgentTerminal.tsx      The live log console — shows what agents are thinking in real time
+-- WorkflowGraph.tsx      Visual SVG diagram of the pipeline that updates live
+-- PlanEditorCard.tsx     The human review gate — shows the AI plan before execution starts
+-- SteeringPanel.tsx      Mid-run intercept — lets you correct the AI if quality is low
+-- AgentCard.tsx          Shows each agent's current status
+-- Timeline.tsx           Visual timeline of which steps are done vs pending
+-- MarkdownRenderer.tsx   Renders the final AI output with proper formatting
+-- Sidebar.tsx            Navigation sidebar
```

**How to explain AgentTerminal.tsx:**
"The frontend opens an EventSource connection to the /stream endpoint.
Every 500 milliseconds the server sends a JSON payload with any new log entries.
AgentTerminal reads those and appends them to the console in real time.
The logs are color-coded by type — thinking, output, error, telemetry, manager decision."

**How to explain PlanEditorCard.tsx:**
"When the backend finishes planning, it sets the task status to awaiting_plan_approval.
The frontend detects this status from the SSE stream and renders the PlanEditorCard.
The user can edit, reorder, or add subtasks.
When they click Approve, the frontend calls the approve_plan endpoint with the modified plan.
There is also a 60-second countdown — if the user does nothing, the pipeline auto-proceeds."

---

## Tests Folder

```
backend/tests/
|
+-- conftest.py                     Sets up a fresh in-memory SQLite database for each test
+-- unit/
|   +-- test_token_budget.py        Tests that tier detection works for different keywords
|   +-- test_security.py            Tests open-access mode and locked mode behavior
|   +-- test_telemetry.py           Tests cost calculation math
|   +-- test_memory_agent.py        Tests cosine similarity calculation
|   +-- test_orchestrator_routing.py  Tests routing function logic
|   +-- test_hitl_timeout.py        Tests the HITL timeout configuration
|   +-- test_evals.py               Tests the evaluation runner and judge
+-- integration/
    +-- test_api_tasks.py           Creates real HTTP requests and checks responses end to end
```

**What to say:** "I separated unit tests from integration tests.
Unit tests are fast — they test one function in isolation with no database or API calls.
Integration tests are slower — they spin up the full FastAPI app
and send real HTTP requests to check that the routes work correctly end to end.
The conftest.py fixture replaces the production database with an in-memory SQLite database
so tests never touch real data."

---

## Key Files to Know by Name

| File | Why an Interviewer Might Ask About It |
|---|---|
| backend/app/workflows/orchestrator.py | This is the brain — explains the entire agent flow |
| backend/app/agents/base.py | Shows understanding of inheritance and DRY principle |
| backend/app/agents/token_budget.py | Shows cost optimization and practical AI thinking |
| backend/app/api/tasks.py | Shows REST API design and SSE streaming implementation |
| backend/app/core/telemetry.py | Shows observability and production engineering mindset |
| backend/app/database/models.py | Shows database design knowledge |
| docker-compose.yml | Shows DevOps and containerization knowledge |
| .env.example | Shows awareness of secrets management |

---

## How to Walk an Interviewer Through the Code

Start at the top and work inward:

1. "The user opens the frontend at localhost:3000 and submits a task."
2. "The frontend calls POST /api/tasks on the FastAPI backend."
3. "FastAPI creates a Task record in the database and starts the orchestrator in the background."
4. "The frontend opens an SSE connection to GET /api/tasks/{id}/stream."
5. "The LangGraph orchestrator starts at the Planner node."
6. "Planner calls Gemini and returns a structured JSON plan. It is saved to the Subtasks table."
7. "The status changes to awaiting_plan_approval. The frontend shows the PlanEditorCard."
8. "User approves. Status goes back to running."
9. "The router calls Memory Agent and Analyst Agent in parallel using asyncio.gather."
10. "Their outputs are aggregated and passed to the Executor."
11. "Executor builds the final deliverable and passes it to the Verifier."
12. "Verifier scores it. If confidence is above 80 percent, task is marked completed."
13. "The SSE stream sends a final event with the result. The frontend displays it."

---

## Common Interview Questions and How to Answer Them

**Why did you use LangGraph instead of just calling agents sequentially?**

"LangGraph gives me a compiled, stateful graph with conditional routing.
The routing logic is a pure function — easy to test.
It also handles the loopback from Verifier back to Executor cleanly.
If I had written sequential code, adding that retry loop would have been messy."

**Why FastAPI and not Flask or Django?**

"FastAPI is built on top of Starlette and supports async natively.
That matters here because I have LLM API calls that take several seconds each.
With async, the server can handle other requests while waiting for Gemini to respond.
Django would have been overkill — I did not need its ORM or admin panel."

**How does the real-time streaming work?**

"Server-Sent Events. The client opens a persistent HTTP connection.
The server polls the database every 500 milliseconds inside an async generator
and yields JSON payloads whenever there are new log entries or status changes.
I also send a comment-only ping every 15 seconds to keep the connection alive through proxies."

**How did you handle costs and performance?**

"Three main optimizations.
First, I combined the web search and reasoning steps into one LLM call instead of two.
Second, I cached the memory embedding so I only generate it once per task instead of twice.
Third, the Memory Agent and Analyst Agent run in parallel, cutting the research phase by 30 to 40 percent."

**How would you scale this?**

"Right now everything runs in one process. To scale, I would move the LangGraph orchestrator
to a task queue like Celery or use LangGraph's built-in persistence with Redis.
I would also move the database to a connection pool like PgBouncer
and put a load balancer in front of multiple FastAPI instances.
The SSE stream would need to be routed to the same instance that holds the session,
or I would switch to a pub-sub system like Redis Pub/Sub."
