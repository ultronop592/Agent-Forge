# AgentForge 🌌

> **Tagline:** *“A collaborative AI workforce that researches, reasons, plans, executes, verifies, and continuously improves complex real-world tasks.”*

---

## 🌟 What is AgentForge? (In Simple Terms)

Most AI applications today are **chatbots** (like ChatGPT or Claude). You ask a question, and a single AI model tries to write an answer on the spot. While this is great for simple questions, chatbots often struggle with complex, multi-step projects because:
1. They try to do everything at once (planning, researching, writing, and editing).
2. They cannot double-check their own work effectively.
3. They get distracted or hallucinate facts during long paragraphs.

**AgentForge is NOT a chatbot.** It is a **Multi-Agent Workforce Platform**. 

Think of AgentForge as a **software company in a box**. Instead of asking one AI model to do everything, AgentForge splits the work among **six specialized AI workers (Agents)**. Each agent has its own job description, its own tools, and its own memory. They work together sequentially, hand off results to one another, and verify the quality of the work before showing it to you.

---

## 👥 Meet the AI Workforce (The 6 Agent Roles)

Here is the organizational chart of your AI workforce:

| Agent Icon | Agent Name | Corporate Role | Responsibilities | Tools Used |
| :---: | :--- | :--- | :--- | :--- |
| 🧭 | **Planner Agent** | *Project Manager / Architect* | Reads your request, breaks it into logical subtasks, and decides which agent should handle each step. | State Decomposer, Graph Scheduler |
| 🔍 | **Research Agent** | *Market & Technical Analyst* | Searches the web, reads references, crawls target pages, and gathers raw documents. | Tavily Search, Mock Crawler |
| 🧠 | **Reasoner Agent** | *Critical Thinker / Critic* | Takes the research, compares statistics, detects contradictions, runs SWOT analyses, and draws logical conclusions. | Logical Synthesizer, SWOT Builder |
| 📝 | **Execution Agent** | *Developer / Document Writer* | Takes the analyzed data and writes the actual final code blocks, markdown reports, or documents. | File Compiler, Report Writer |
| 🛡️ | **Verifier Agent** | *Quality Assurance (QA) Inspector* | Fact-checks the executor's output against the user's initial goal, flags errors or hallucinations, and scores confidence. | Consistency Asserter, Quality Scorer |
| 📁 | **Memory Agent** | *Librarian / Historian* | Queries historical task results to find context, and saves new lessons learned to the database for future runs. | SQLite Semantic Searcher, DB Writer |

---

## 🔄 How the Workforce Collaborates (Step-by-Step Flow)

Let’s look at what happens under the hood when you submit a goal like: **"Research the AI startup market."**

```
 [User Prompt]
      │
      ▼
┌──────────────┐
│ Planner      │ ──► Reads the prompt and generates a list of 4 subtasks
└──────────────┘
      │
      ▼
┌──────────────┐
│ Memory       │ ──► Searches the database to see if we did a similar task before
└──────────────┘
      │
      ▼
┌──────────────┐
│ Researcher   │ ──► Searches the web (via Tavily) to collect competitor names & trends
└──────────────┘
      │
      ▼
┌──────────────┐
│ Reasoner     │ ──► Compares the research, isolates discrepancies, and runs a SWOT analysis
└──────────────┘
      │
      ▼
┌──────────────┐
│ Executor     │ ──► Compares the reasoning notes and writes a formatted Markdown report
└──────────────┘
      │
      ▼
┌──────────────┐
│ Verifier     │ ──► Reviews the report, runs factual checks, and scores it (e.g. 95% Confidence)
└──────────────┘
      │
      ▼
 [Final Report] ──► Rendered beautifully on the User Dashboard
```

---

## 🛠️ The Tech Stack (Explained Simply)

AgentForge is built using a modern, production-grade tech stack:

### 1. **Next.js & React (Frontend Dashboard)**
The visual command center of the application. Instead of showing a simple chat input, the UI uses **dark glassmorphism panels** and **animations** to display:
- **Workflow Graph**: An active node graph showing which agent is currently active and thinking.
- **Agent Terminal**: A monospace console window showing live "internal thoughts" and tool calls in real time.
- **Execution Timeline**: A step-by-step progress checklist of completed subtasks.
- **Verified Output**: A clean Markdown document viewer.

### 2. **FastAPI (Backend API)**
The coordinator of the application. It receives requests from the frontend, writes information to the database, manages background threads, and streams updates to the frontend using **Server-Sent Events (SSE)**.

### 3. **LangGraph (Workflow State Machine)**
This is the brain of the backend workflow. LangGraph allows us to define the agents as **nodes** in a flowchart (graph) and connect them with **edges** (rules). It maintains the "Shared State" (the project file) and passes it from agent to agent.

### 4. **Google GenAI SDK (Gemini 2.5 Flash)**
The engine powering all AI reasoning. We use `Gemini 2.5 Flash` for its lightning-fast speed, large context window (perfect for processing massive search files), and structured JSON output capabilities.

### 5. **Model Context Protocol (MCP)**
An open standard (developed by Anthropic) that allows AI models to connect to external servers easily. AgentForge has a built-in MCP manager that can run subprocesses (like standard Node or Python scripts) and translate their tools (like reading a file or searching a database) so the agents can use them.

---

## 📂 Folder Structure Map

Here is the blueprint of where everything is located:

```
agentforge/
│
├── backend/                       # BACKEND CODE (Python & FastAPI)
│   ├── app/
│   │   ├── api/                   # API Endpoints (The URLs the frontend talks to)
│   │   │   ├── agents.py          # Returns list of active agents and their tools
│   │   │   ├── mcp.py             # Registers and tests external MCP servers
│   │   │   ├── memory.py          # Queries and adds entries to the memory bank
│   │   │   ├── plugins.py         # Lists active workflow configurations
│   │   │   └── tasks.py           # Creates tasks and streams live logs via SSE
│   │   │
│   │   ├── agents/                # Individual Agent Definitions
│   │   │   ├── base.py            # BaseAgent class (handles Gemini API calls & fallback)
│   │   │   ├── planner.py         # Planner Agent (creates subtask checklist)
│   │   │   ├── researcher.py      # Researcher Agent (Tavily search & crawlers)
│   │   │   ├── reasoner.py        # Reasoner Agent (SWOT analysis & gap checking)
│   │   │   ├── executor.py        # Executor Agent (writes markdown reports & code)
│   │   │   ├── verifier.py        # Verifier Agent (fact-checks & confidence scores)
│   │   │   └── memory_agent.py    # Memory Agent (recalls past insights)
│   │   │
│   │   ├── core/                  # System core settings
│   │   │   └── config.py          # Loads keys and database URLs from .env
│   │   │
│   │   ├── database/              # SQLite Database Configuration
│   │   │   ├── connection.py      # Opens the database session
│   │   │   └── models.py          # Defines DB tables (Tasks, Subtasks, Logs, Memory)
│   │   │
│   │   ├── mcp/                   # Model Context Protocol (MCP) Manager
│   │   │   └── client.py          # Spawns MCP stdio servers and handles JSON-RPC
│   │   │
│   │   ├── plugins/               # Workflow Plugins Directory
│   │   │   ├── base_plugin.py     # Base abstract class for plugins
│   │   │   ├── registry.py        # Holds the list of active workflows
│   │   │   ├── software_debug.py  # Plugin workflow: Diagnosing and fixing code
│   │   │   └── startup_research.py# Plugin workflow: Market sizing and SWOT
│   │   │
│   │   ├── workflows/             # LangGraph Configurations
│   │   │   ├── state.py           # Defines the shared data dictionary
│   │   │   └── orchestrator.py    # Compiles the flowchart links (Nodes & Edges)
│   │   │
│   │   └── main.py                # FastAPI boot entry point
│   │
│   ├── requirements.txt           # Python library dependencies
│   ├── test_system.py             # Automated test script to verify compilation
│   └── Dockerfile                 # Docker setup for the backend
│
├── frontend/                      # FRONTEND CODE (Next.js, TypeScript & React)
│   ├── src/
│   │   ├── app/                   # Next.js Pages (App Router)
│   │   │   ├── chat/              # Workspace / Execution viewport page
│   │   │   ├── mcp/               # MCP Console (add servers & test tools)
│   │   │   ├── memory/            # Memory bank viewer
│   │   │   ├── plugins/           # Installed workflows & marketplace placeholder
│   │   │   ├── layout.tsx         # Shell wrapping pages with Sidebar
│   │   │   ├── globals.css        # Global styles, scrollbars, and keyframes
│   │   │   └── page.tsx           # Main Dashboard (displays metrics & history)
│   │   │
│   │   ├── components/            # Reusable React UI widgets
│   │   │   ├── AgentCard.tsx      # Displays single agent status (pulsing, thinking)
│   │   │   ├── AgentTerminal.tsx  # Monospace console streaming thoughts
│   │   │   ├── MarkdownRenderer.tsx # Renders Markdown documents & custom alerts
│   │   │   ├── Sidebar.tsx        # Left navigation pane with health status
│   │   │   ├── Timeline.tsx       # Timeline progress tracker
│   │   │   └── WorkflowGraph.tsx  # Interactive SVG graph showing live flows
│   │   │
│   │   └── lib/
│   │       └── api.ts             # Central API client helpers
│   │
│   ├── package.json               # Frontend Node package file
│   └── Dockerfile                 # Multi-stage Docker builder for Next.js
│
├── docker-compose.yml             # Orchestration script to run frontend + backend together
└── README.md                      # This master guide
```

---

## ⚡ Setup & Run Guidelines

Follow these simple instructions to set up and run AgentForge on your local machine:

### 1. Configure Credentials
Copy the `.env.example` file in the root directory to a new file named `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in your keys:
- **GEMINI_API_KEY**: Get it for free at [Google AI Studio](https://aistudio.google.com/). *(Note: If this key is missing, AgentForge will automatically run in a **demo/mock mode** so you can test the UI animations and workflows immediately without spending API credits!)*
- **TAVILY_API_KEY**: Get a search API key at [Tavily](https://tavily.com/).

---

### 2. Run Locally (Traditional Way)

You will need **Python (3.11 or higher)** and **Node.js (v20 or higher)** installed.

#### **Backend Setup:**
1. Open a terminal and go into the `backend` folder:
   ```bash
   cd backend
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the automated integration test script to verify everything compiles:
   ```bash
   python test_system.py
   ```
5. Start the FastAPI backend server:
   ```bash
   python -m app.main
   ```
   *The backend is now running at: [http://localhost:8000](http://localhost:8000)*

#### **Frontend Setup:**
1. Open a new terminal and go into the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install NPM dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js dev server:
   ```bash
   npm run dev
   ```
   *The frontend is now running at: [http://localhost:3000](http://localhost:3000)*

---

### 3. Run with Docker (Easiest Way)

If you have Docker installed, you can launch everything with a single command without installing Python or Node.js on your computer:

1. Open your terminal in the root folder (where `docker-compose.yml` is located).
2. Run:
   ```bash
   docker-compose up --build
   ```
3. Access the application in your browser:
   - **Frontend UI Control Deck**: [http://localhost:3000](http://localhost:3000)
   - **FastAPI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔌 How to Add Custom Plugins (Workflows)

Each workspace workflow is a **Plugin**. AgentForge comes with two default plugins:
- **Startup Market Research**: Step 1 (Memory) → Step 2 (Research) → Step 3 (Reasoning) → Step 4 (Execution) → Step 5 (Verification).
- **Software Debugging Suite**: Step 1 (Research) → Step 2 (Reasoning) → Step 3 (Execution) → Step 4 (Verification).

You can add a new plugin (for example, *Resume Review* or *Medical Audit*) in **3 simple steps**:

### Step 1: Create the Plugin Class
Create a new file in `backend/app/plugins/resume_review.py`:
```python
from typing import List, Dict, Any
from backend.app.plugins.base_plugin import BaseWorkflowPlugin

class ResumeReviewPlugin(BaseWorkflowPlugin):
    @property
    def name(self) -> str:
        return "Resume Quality Review"

    @property
    def plugin_id(self) -> str:
        return "resume_review"

    @property
    def description(self) -> str:
        return "Evaluates candidate resumes against job descriptions, identifies skill gaps, and drafts emails."

    def get_custom_system_instruction(self, agent_name: str) -> str:
        # Give agents customized roles instructions inside this plugin
        if agent_name == "Planner":
            return "You are an HR Director Planner. Partition resume audits."
        elif agent_name == "Reasoner":
            return "You are a recruitment specialist. Compare resume skills against job requirements."
        elif agent_name == "Executor":
            return "You are a professional copywriter. Draft recommendations and candidate emails."
        return ""

    def get_default_subtasks(self, prompt: str) -> List[Dict[str, Any]]:
        # Define step configurations
        return [
            {
                "title": "Analyze Resume Content",
                "description": f"Read resume skills and search references matching: {prompt}",
                "assigned_agent": "researcher",
                "order_index": 0
            },
            {
                "title": "Evaluate Job Alignment",
                "description": "Perform comparative audit, find matching skills, and list missing experience.",
                "assigned_agent": "reasoner",
                "order_index": 1
            },
            {
                "title": "Draft HR Evaluation Report",
                "description": "Draft candidate profile scorecard and write personalized recruitment outreach email.",
                "assigned_agent": "executor",
                "order_index": 2
            },
            {
                "title": "Verify Output Factual Integrity",
                "description": "Ensure candidate score is correct, spelling is clean, and output is polished.",
                "assigned_agent": "verifier",
                "order_index": 3
            }
        ]
```

### Step 2: Register the Plugin
Open `backend/app/plugins/registry.py` and register the new plugin:
```diff
# Import plugins to register them
from backend.app.plugins.software_debug import SoftwareDebugPlugin
from backend.app.plugins.startup_research import StartupResearchPlugin
+from backend.app.plugins.resume_review import ResumeReviewPlugin

plugin_registry.register(SoftwareDebugPlugin())
plugin_registry.register(StartupResearchPlugin())
+plugin_registry.register(ResumeReviewPlugin())
```

### Step 3: Refresh and Run
Boot the application. The workspace dropdown in Next.js will automatically list **"Resume Quality Review"**! Selecting it will instantly trigger the new 4-stage workflow sequence.

---

## 🔮 Future Roadmap (Scale to SaaS)

1. **Vector DB Integration**: Replace the SQLite memory database with a vector database (likepgvector, ChromaDB, or Pinecone) to enable semantic "embedding similarity" searches instead of keyword matches.
2. **Containerized MCP Sandboxing**: Run external node/python MCP scripts inside isolated Docker containers (using python-on-whales) to run filesystems read/write safely in staging/production.
3. **Graph Loopback Revisions**: Modify the LangGraph flow so that if the Verifier Agent flags a factual error (low confidence score), it rejects the task and loops back to the Executor Agent with feedback to fix the report before showing it to the user.
4. **Bidirectional WebSockets**: Move log streaming from one-way Server-Sent Events (SSE) to WebSockets, enabling users to enter terminal prompts dynamically during execution.
