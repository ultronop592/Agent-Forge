"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { 
  Play, 
  ArrowRight,
  Sparkles, 
  Search, 
  ShieldCheck, 
  Users,
  Code2,
  BrainCircuit,
  History,
  ChevronRight,
  Puzzle,
  Terminal,
  Compass
} from "lucide-react";

interface Task {
  id: string;
  prompt: string;
  status: "pending" | "running" | "completed" | "failed";
  plugin_name: string;
  created_at: string;
}

interface Plugin {
  plugin_id: string;
  name: string;
  description: string;
}

type ObjectiveMode = "code" | "research" | "reasoning" | "qa";

const MODES = [
  {
    id: "code" as ObjectiveMode,
    label: "Write & Debug Code",
    icon: Code2,
    pluginId: "software_debugging",
    placeholder: "Describe code to write or bug to diagnose (e.g. 'Implement a thread-safe Redis token bucket rate limiter in Python' or 'Create a Next.js auth client')...",
    suggestions: [
      { label: "Python Redis Rate Limiter", prompt: "Implement a thread-safe Redis token bucket rate limiter in Python adhering to SOLID design principles." },
      { label: "FastAPI WebSocket Manager", prompt: "Build an asynchronous FastAPI connection manager for real-time WebSocket broadcast with heartbeat checks." },
      { label: "JWT Auth Middleware", prompt: "Create a production-grade TypeScript JWT authentication middleware with refresh token rotation." }
    ]
  },
  {
    id: "research" as ObjectiveMode,
    label: "Live Web Research",
    icon: Search,
    pluginId: "startup_research",
    placeholder: "Describe market or live web topic (e.g. 'Search and aggregate AI Developer job openings posted today in India with salary estimates')...",
    suggestions: [
      { label: "AI Jobs in India", prompt: "Search and aggregate AI Developer job openings posted today in India with salary estimates and direct URLs." },
      { label: "Multi-Agent SWOT Analysis", prompt: "Perform market intelligence and competitive SWOT analysis for autonomous multi-agent orchestration frameworks." },
      { label: "2026 AI Agent Sizing", prompt: "Conduct comprehensive market sizing, enterprise CAGR projections, and competitor audits for AI agent frameworks." }
    ]
  },
  {
    id: "reasoning" as ObjectiveMode,
    label: "Architecture & Strategy",
    icon: BrainCircuit,
    pluginId: "software_debugging",
    placeholder: "Describe technical architecture or strategy to evaluate (e.g. 'Design an event-driven microservices architecture with Kafka')...",
    suggestions: [
      { label: "Event-Driven Architecture", prompt: "Design an event-driven microservices architecture for high-throughput financial transactions with idempotency." },
      { label: "Postgres Sharding Strategy", prompt: "Outline a zero-downtime horizontal database sharding strategy for PostgreSQL handling 100M+ rows." },
      { label: "OAuth2 vs Session Auth", prompt: "Analyze trade-offs between stateless JWT tokens versus stateful Redis sessions for enterprise multi-tenant applications." }
    ]
  },
  {
    id: "qa" as ObjectiveMode,
    label: "Fact-Check & QA",
    icon: ShieldCheck,
    pluginId: "startup_research",
    placeholder: "Paste claims, documentation, or technical requirements for multi-agent factual verification and automated QA judging...",
    suggestions: [
      { label: "Audit Security Vulnerabilities", prompt: "Perform a security compliance audit for OAuth2 PKCE flows and identify potential CSRF/XSS vectors." },
      { label: "Fact-Check Market Claims", prompt: "Fact-check and verify latest published LLM inference cost metrics across Anthropic, OpenAI, and Google Gemini." },
      { label: "Verify Python Concurrency", prompt: "Verify thread-safety and dead-lock prevention in Python multithreaded queue consumers." }
    ]
  }
];

const CAPABILITIES = [
  {
    title: "Live Web Grounding",
    icon: Search,
    desc: "Crawls real-time web sources via Tavily & DuckDuckGo with verified citations and zero fake links."
  },
  {
    title: "Multi-Agent Collaboration",
    icon: Users,
    desc: "Autonomous division of labor across planning, reasoning, and code synthesis agents."
  },
  {
    title: "Fact-Checked QA Gates",
    icon: ShieldCheck,
    desc: "Automated LLM-as-a-Judge evaluates deliverable quality and scores confidence ratings (95%+)."
  }
];

export default function Dashboard() {
  const router = useRouter();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [selectedPlugin, setSelectedPlugin] = useState("");
  const [activeMode, setActiveMode] = useState<ObjectiveMode>("code");
  const [prompt, setPrompt] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [tasksData, pluginsData] = await Promise.all([
          api.getTasks().catch(() => []),
          api.getPlugins().catch(() => [])
        ]);
        setTasks(tasksData);
        setPlugins(pluginsData);
        if (pluginsData.length > 0) {
          setSelectedPlugin(pluginsData[0].plugin_id);
        }
      } catch (e) {
        console.error("Failed to load dashboard data:", e);
      }
    };
    loadData();
  }, []);

  const handleSelectMode = (mode: typeof MODES[0]) => {
    setActiveMode(mode.id);
    const matching = plugins.find(p => p.plugin_id === mode.pluginId);
    if (matching) {
      setSelectedPlugin(matching.plugin_id);
    }
  };

  const currentModeConfig = MODES.find(m => m.id === activeMode) || MODES[0];

  const handleLaunch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isSubmitting || !selectedPlugin) return;

    setIsSubmitting(true);
    try {
      const task = await api.createTask(prompt, selectedPlugin);
      router.push(`/chat?task_id=${task.id}`);
    } catch (err) {
      console.error("Task creation failed:", err);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-6 md:p-10 max-w-5xl mx-auto space-y-11 w-full relative z-10 bg-[#121214] text-[#f4f4f5]">
      {/* 1. Claude-Style Centered Greeting & Header */}
      <div className="text-center space-y-4 pt-2 md:pt-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#da7756]/10 border border-[#da7756]/30 text-[#da7756] text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Autonomous AI Workforce</span>
        </div>

        <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-white leading-tight">
          What would you like the workforce <br />
          to <span className="text-[#da7756]">build or solve?</span>
        </h1>

        <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-zinc-400 max-w-2xl mx-auto pt-1 font-medium">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#da7756]" />
            Multi-agent collaborative planning, research & code synthesis
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#da7756]" />
            Real-time live web grounding with zero hallucinated links
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            Automated LLM-as-a-Judge QA verification (95%+ accuracy)
          </span>
        </div>
      </div>

      {/* 2. Interactive Objective Modes + Central Dispatcher */}
      <div className="max-w-3xl mx-auto space-y-3">
        
        {/* Mode Selector Tabs (Code, Research, Architecture, QA) */}
        <div className="flex items-center justify-center gap-2 flex-wrap">
          {MODES.map((mode) => {
            const Icon = mode.icon;
            const isSelected = activeMode === mode.id;
            return (
              <button
                key={mode.id}
                type="button"
                onClick={() => handleSelectMode(mode)}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                  isSelected
                    ? "bg-[#da7756]/15 text-white border border-[#da7756]/50"
                    : "bg-[#18181b] text-zinc-400 hover:text-white border border-zinc-800 hover:border-zinc-700"
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isSelected ? "text-[#da7756]" : "text-zinc-400"}`} />
                <span>{mode.label}</span>
              </button>
            );
          })}
        </div>

        {/* Claude-Style Central Goal Dispatcher Box */}
        <form 
          onSubmit={handleLaunch} 
          className="glass-panel rounded-2xl p-4 md:p-5 border border-zinc-800 bg-[#18181b] space-y-3.5 focus-within:border-[#da7756]/60 transition-colors shadow-none"
        >
          <textarea
            rows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={currentModeConfig.placeholder}
            className="w-full bg-transparent text-sm text-white placeholder-zinc-500 focus:outline-none resize-none leading-relaxed"
          />

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-zinc-800/80">
            {/* Blueprint Selector */}
            <div className="flex items-center gap-2">
              <Puzzle className="w-3.5 h-3.5 text-[#da7756] shrink-0" />
              <select
                value={selectedPlugin}
                onChange={(e) => setSelectedPlugin(e.target.value)}
                className="bg-[#121214] border border-zinc-800 rounded-lg px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-[#da7756]/60 cursor-pointer max-w-xs truncate"
              >
                {plugins.map((p) => (
                  <option key={p.plugin_id} value={p.plugin_id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Launch Button */}
            <button
              type="submit"
              disabled={isSubmitting || !prompt.trim()}
              className="px-5 py-2.5 rounded-xl bg-[#da7756] hover:bg-[#c96a4a] text-white font-bold text-xs flex items-center justify-center gap-2 disabled:opacity-40 transition-colors cursor-pointer shrink-0"
            >
              {isSubmitting ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Planning Subtasks...</span>
                </>
              ) : (
                <>
                  <Play className="w-3 h-3 fill-white" />
                  <span>Deploy Workforce</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Quick Suggestion Chips Tailored to Active Mode */}
        <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
          <span className="text-[11px] text-zinc-500 font-medium mr-1">Suggestions:</span>
          {currentModeConfig.suggestions.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setPrompt(preset.prompt)}
              className="px-3 py-1 rounded-full bg-[#18181b] border border-zinc-800 text-zinc-300 hover:text-white hover:border-[#da7756]/50 text-xs font-medium transition cursor-pointer text-left"
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* 3. Core Workforce Pillars (3 Minimal Cards) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {CAPABILITIES.map((cap, idx) => {
          const Icon = cap.icon;
          return (
            <div key={idx} className="glass-panel rounded-2xl p-5 border border-zinc-800 space-y-2 bg-[#18181b]">
              <div className="w-8 h-8 rounded-lg bg-[#da7756]/15 border border-[#da7756]/20 text-[#da7756] flex items-center justify-center">
                <Icon className="w-4 h-4" />
              </div>
              <h3 className="text-xs font-bold text-white">{cap.title}</h3>
              <p className="text-[11px] text-zinc-400 leading-relaxed font-normal">
                {cap.desc}
              </p>
            </div>
          );
        })}
      </div>

      {/* 4. Compact Bottom Overview (Workforce Roster Link & Recent Activity) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left: Specialized Agents Roster Banner (span 5) */}
        <div className="lg:col-span-5 glass-panel rounded-2xl p-6 border border-zinc-800 flex flex-col justify-between space-y-4 bg-[#18181b]">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-[#da7756]" />
              <h3 className="text-sm font-bold text-white">Specialized AI Agents</h3>
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Explore the 5 specialized autonomous agents configured with tool capabilities, token budgets, and LLM verification gates.
            </p>
          </div>

          <Link
            href="/agents"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#da7756] hover:text-[#e08569] transition group"
          >
            <span>View Workforce Roster</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>

        {/* Right: Recent Launches Mini Strip (span 7) */}
        <div className="lg:col-span-7 glass-panel rounded-2xl p-6 border border-zinc-800 space-y-3.5 bg-[#18181b]">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-[#da7756]" />
              <h3 className="text-sm font-bold text-white">Recent Deployments</h3>
            </div>
            <Link
              href="/recent"
              className="text-xs font-semibold text-[#da7756] hover:text-[#e08569] flex items-center gap-1"
            >
              <span>View All</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {tasks.length === 0 ? (
            <div className="text-zinc-500 text-xs italic py-4 text-center">
              No recent workspaces launched yet. Select a mode above to get started.
            </div>
          ) : (
            <div className="space-y-2">
              {tasks.slice(0, 3).map((t) => (
                <Link
                  key={t.id}
                  href={`/chat?task_id=${t.id}`}
                  className="flex items-center justify-between p-2.5 rounded-xl bg-[#121214] border border-zinc-800/80 hover:border-zinc-700 transition group text-xs"
                >
                  <span className="text-zinc-300 font-medium truncate max-w-sm" title={t.prompt}>
                    {t.prompt}
                  </span>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full border uppercase ${
                      t.status === "completed"
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                        : t.status === "running"
                        ? "bg-[#da7756]/10 text-[#da7756] border-[#da7756]/20"
                        : "bg-zinc-900 text-zinc-500 border-zinc-800"
                    }`}>
                      {t.status}
                    </span>
                    <ArrowRight className="w-3 h-3 text-zinc-500 group-hover:text-[#da7756] transition" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
