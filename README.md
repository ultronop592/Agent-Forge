# AgentForge 🌌

[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-orange?style=flat-square&logo=python)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-black?style=flat-square&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![Gemini 2.5](https://img.shields.io/badge/Gemini_2.5-Flash-blue?style=flat-square&logo=google&logoColor=white)](https://aistudio.google.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791?style=flat-square&logo=postgresql&logoColor=white)](https://neon.tech)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com)
[![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=flat-square&logo=render&logoColor=white)](https://render.com)

> *"A self-healing, high-speed AI workforce that plans, researches, executes, verifies, and coordinates complex real-world tasks in parallel with zero-overhead supervision, extensibility via MCP servers, and specialized workflow plugins."*

---

## 🌟 What is AgentForge?

AgentForge is an **Autonomous Multi-Agent Workforce Platform** — a coordinated team of specialized AI workers operating under an orchestration graph.

Instead of relying on a single slow, error-prone prompt attempt, AgentForge breaks complex user goals into subtasks, delegates them to role-specific agents (**Planner**, **Manager**, **Memory**, **Analyst**, **Executor**, **Verifier**), and streams live progress with self-healing verification loops.

---

## ✨ Production-Grade Features & Recent Upgrades

| Feature | Status | Description |
| :--- | :---: | :--- |
| ⚡ **Parallel Subtask Execution** | ✅ Shipped | `MemoryAgent` and `AnalystAgent` run concurrently via Python's `asyncio.gather()`, cutting research latency by **30%–40%**. |
| 📉 **5-API-Call Optimization** | ✅ Shipped | Reduced pipeline overhead from 10+ calls to **5 API calls max** by unifying search & reasoning into `AnalystAgent` and reusing query embeddings. |
| 👑 **0-Cost Manager Coordinator** | ✅ Shipped | The Manager Agent operates as a zero-LLM-cost supervisor, logging pipeline transitions, parallel dispatches, and markdown run summaries. |
| 🛰️ **Production SSE Streaming** | ✅ Shipped | Real-time Server-Sent Events with `X-Accel-Buffering: no` proxy headers, 15s `: ping` heartbeats, and exponential backoff auto-reconnect. |
| 🔁 **Self-Healing Verification** | ✅ Shipped | Automatic QA feedback loops rerouting back to the Executor for correction when confidence falls below threshold (up to 3 retries). |
| 🧠 **Cross-Task Vector Memory** | ✅ Shipped | Cosine similarity vector search over 3072-dimensional `gemini-embedding-001` embeddings with automatic task archiving and `🎯 XX% Match` UI badges. |
| 🔌 **Model Context Protocol (MCP)** | ✅ Shipped | Connect and manage external `stdio` tool servers, inspect JSON-RPC schemas, and invoke tools directly from the workspace. |
| 🧩 **Workflow Plugin Engine** | ✅ Shipped | Modular workflow presets (e.g., *Startup Market Research*, *Software Debugging Suite*) with custom persona overrides and default task chains. |
| 🐘 **Neon PostgreSQL Integration** | ✅ Shipped | Production connection pooling with `pool_pre_ping=True` and serverless PostgreSQL support on Render. |

---

## 👥 The Agent Workforce

| Icon | Agent | Role | Responsibility |
| :---: | :--- | :--- | :--- |
| 🧭 | **Planner** | Lead Architect | Decomposes user goals into structured subtasks. |
| 👑 | **Manager** | Orchestration Supervisor | Coordinates routing, logs parallel dispatches, and builds final run summaries (**0 LLM cost**). |
| 📁 | **Memory** | Institutional Librarian | Retrieves past task insights via semantic cosine similarity vector search. |
| 🔍 | **Analyst** | Research & SWOT Analyst | Conducts live web research (Tavily) + critical SWOT analysis in 1 unified step. |
| 📝 | **Executor** | Deliverable Builder | Synthesizes prior context and builds final code, reports, or data files. |
| 🛡️ | **Verifier** | QA Fact-Checker | Fact-checks output against requirements, scores confidence, and triggers self-healing loops. |

---

## 🔌 Model Context Protocol (MCP) Integration

AgentForge natively implements Anthropic's **Model Context Protocol (MCP)** standard. This allows the workforce to securely connect to external tool servers (filesystem, databases, web scraping, API runners) using JSON-RPC over stdio/HTTP.

### Key Capabilities:
- **Server Registry:** Add, remove, and monitor external MCP servers via the `/mcp` management dashboard or REST API (`/api/mcp/servers`).
- **Dynamic Tool Discovery:** Discovers available tools and parameters from registered MCP servers automatically.
- **Interactive Tool Execution:** Test tool calls directly from the UI with custom JSON payloads.

```
+-------------------+       JSON-RPC over stdio      +-------------------------+
| AgentForge Engine | <===========================> | MCP Server (Python/Node)|
+-------------------+                               +-------------------------+
        |                                                        |
        v                                                        v
 [Task Execution]                                        [Filesystem / Database]
```

---

## 🧩 Workflow Plugins System

AgentForge supports domain-specific **Workflow Plugins** that alter agent system instructions, inject specialized prompts, and configure default subtask sequences.

### Built-in Plugins:

1. **📈 Startup Market Research Plugin**
   - **Persona Overrides:** Transforms Planner into a *VC Principal*, Analyst into a *Business Intelligence Analyst*, Reasoner into a *Strategy Advisor*, and Executor into a *Pitch Deck Writer*.
   - **Deliverables:** Competitor matrix, TAM/SAM/SOM market sizing tables, SWOT analysis, and risk registers.

2. **🐛 Software Debugging Suite Plugin**
   - **Persona Overrides:** Transforms Planner into a *Principal Systems Architect*, Analyst into a *Root-Cause Analyst*, and Executor into a *Senior Software Engineer*.
   - **Deliverables:** Bug diagnostics, root cause explanation, SOLID-compliant code fix, edge-case unit tests, and usage documentation.

```python
# Plugins inherit from BaseWorkflowPlugin
class StartupResearchPlugin(BaseWorkflowPlugin):
    @property
    def plugin_id(self) -> str:
        return "startup_research"

    def get_custom_system_instruction(self, agent_name: str) -> str:
        if agent_name == "Planner":
            return "You are a Venture Capital Principal Planner..."
```

---

## 🔄 Workforce Graph Architecture

```mermaid
graph TD
    User([🧑 User Goal + Plugin Selection]) --> Planner[🧭 Planner Agent]
    Planner --> Manager[👑 Manager Supervisor]

    subgraph LangGraph State Machine
        Manager -->|Parallel Dispatch via asyncio.gather| ParallelStage{⚡ Parallel Research Stage}

        subgraph Concurrent Execution
            ParallelStage --> Memory[📁 Memory Agent]
            ParallelStage --> Analyst[🔍 Analyst Agent]
        end

        Memory --> Join[⚡ Aggregator]
        Analyst --> Join

        Join --> Executor[📝 Executor Agent]
        Executor --> Verifier[🛡️ Verifier Agent]

        Verifier -->|is_valid = true OR retries exhausted| Done[✅ Task Complete & Saved to Memory]
        Verifier -->|is_valid = false AND retry_count < 3| Executor
    end

    Done -->|SSE Stream + Heartbeat| UI[🖥️ Next.js Glassmorphism Console]
```

---

## ⚡ Latency & Token Optimization Engineering

### 1. Unified Search + Reasoning (`AnalystAgent`)
Previously, Web Search and Critical Reasoning were split across 2 separate LLM calls. The `AnalystAgent` now performs both in a single step, saving **1 full LLM API call** and **6+ seconds of latency**.

### 2. Zero-Cost Embedding Reuse
When `MemoryAgent` computes the 3072-dimensional vector embedding for searching past context, it caches the vector in `AgentState`. When saving final task lessons at the end, `MemoryAgent` reuses the cached embedding — eliminating **1 extra embedding API call**.

### 3. Non-Blocking SSE Heartbeats
To survive proxy idle timeouts (like Render's 55s limit), the `/tasks/{id}/stream` generator emits a `: ping` comment every 15 seconds. Frontend `EventSource` connections stay alive across long-running agent execution.

### 4. Large Output Safeguard in QA
Executor deliverables exceeding 6,000 characters are safely truncated for the Verifier's LLM prompt, preventing token-limit hangs while preserving 100% of the original content in the final verified result.

---

## 🛠️ Tech Stack

- **Backend Framework:** FastAPI + LangGraph + SQLAlchemy
- **Protocol Standards:** Model Context Protocol (MCP) + SSE
- **Database:** Neon PostgreSQL (Production) / SQLite (Local)
- **AI Models:** Gemini 2.5 Flash + `gemini-embedding-001`
- **Search Engine:** Tavily Search API
- **Frontend App:** Next.js 16 (App Router, React 19, Tailwind CSS)
- **Deployment:** Render (Backend API & DB) + Vercel (Frontend)

---

## 📂 Folder Structure

```
agentforge/
│
├── backend/                    # Python FastAPI & LangGraph Engine
│   ├── app/
│   │   ├── api/                # REST & SSE Endpoints (tasks, agents, memory, mcp, plugins)
│   │   ├── agents/             # Agent definitions (planner, manager, memory, analyst, executor, verifier)
│   │   │   ├── base.py         # BaseAgent with rate-limit retries & DB logging
│   │   │   ├── manager_agent.py# 0-cost Orchestration Coordinator
│   │   │   ├── analyst_agent.py# Unified Search + SWOT Reasoning
│   │   │   ├── executor.py     # Deliverable Builder with feedback loop
│   │   │   ├── verifier.py     # QA Fact-Checker with truncation safeguard
│   │   │   └── memory_agent.py # Cosine Similarity Vector Search
│   │   ├── database/           # Neon PostgreSQL / SQLite models & connection pool
│   │   ├── mcp/                # MCP JSON-RPC Client & Server Manager
│   │   ├── plugins/            # Workflow Plugin Registry & Implementations
│   │   └── workflows/
│   │       ├── state.py        # AgentState TypedDict
│   │       └── orchestrator.py # LangGraph workflow with parallel_research_node
│
├── frontend/                   # Next.js 16 Dashboard UI
│   └── src/
│       ├── app/                # Pages (Workspace, Memory, MCP, Plugins, Dashboard)
│       ├── components/         # WorkflowGraph, AgentTerminal (LIVE badge), AgentCard, Timeline
│       └── lib/                # API & SSE client helpers
│
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone & Configure
```bash
git clone https://github.com/ultronop592/Agent-Forge.git
cd Agent-Forge
cp .env.example .env
# Add GEMINI_API_KEY and TAVILY_API_KEY to .env
```

### 2. Start Backend
```bash
pip install -r backend/requirements.txt
python -m backend.app.main
```

### 3. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` to launch the **AI Workforce Workspace**.

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
