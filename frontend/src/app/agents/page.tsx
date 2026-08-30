"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import AgentCard from "@/components/AgentCard";
import { Users, Compass, Search, BrainCircuit, FileCode, ShieldCheck, FolderGit, Sparkles, ArrowRight } from "lucide-react";
import Link from "next/link";

interface Agent {
  name: string;
  role: string;
  status: "idle" | "thinking" | "tool_call" | "completed" | "failed";
  description: string;
  tools: string[];
}

const AGENT_SPECIALIZATIONS = [
  {
    role: "Planner Agent",
    icon: Compass,
    specialty: "Goal Decomposition & Human-in-the-Loop",
    summary: "Deconstructs complex goals into deterministic subtasks with human approval gates."
  },
  {
    role: "Analyst & Researcher",
    icon: Search,
    specialty: "Live Grounded Web Intelligence",
    summary: "Queries real-time web engines (Tavily/DuckDuckGo) with zero fake hallucinated sources."
  },
  {
    role: "Executor Agent",
    icon: FileCode,
    specialty: "Code Synthesis & Technical Deliverables",
    summary: "Produces production-grade code, data structures, and verified reports."
  },
  {
    role: "Verifier & QA Judge",
    icon: ShieldCheck,
    specialty: "LLM-as-a-Judge Fact Checking",
    summary: "Scores deliverable accuracy (95%+ target) and triggers steering on quality discrepancies."
  },
  {
    role: "Memory Agent",
    icon: FolderGit,
    specialty: "Vector Semantic Recall",
    summary: "Stores and retrieves historic patterns, code snippets, and factual constraints."
  }
];

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    const loadAgents = async () => {
      try {
        const data = await api.getAgents();
        setAgents(data);
      } catch (e) {
        console.error("Failed to load agents:", e);
      } finally {
        setLoading(false);
      }
    };
    loadAgents();
    const interval = setInterval(loadAgents, 8000);
    return () => clearInterval(interval);
  }, []);

  const filteredAgents = agents.filter((a) => {
    if (filter === "all") return true;
    return a.status === filter;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-9 w-full relative z-10 bg-[#121214] text-[#f4f4f5]">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-[#da7756]/15 border border-[#da7756]/30 text-[#da7756] flex items-center justify-center">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">
                Autonomous Agent Workforce Roster
              </h2>
              <p className="text-zinc-400 text-xs mt-0.5 max-w-2xl">
                Specialized LLM agent nodes configured with distinct system directives, tool capabilities, and QA verification gates.
              </p>
            </div>
          </div>
        </div>

        <Link
          href="/chat"
          className="px-4 py-2.5 rounded-xl bg-[#da7756] hover:bg-[#c96a4a] text-white text-xs font-bold flex items-center gap-2 transition-colors self-start md:self-center"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Deploy Workforce</span>
        </Link>
      </div>

      {/* Workforce Architecture Highlights */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        {AGENT_SPECIALIZATIONS.map((spec, idx) => {
          const Icon = spec.icon;
          return (
            <div key={idx} className="glass-panel rounded-2xl p-4 border border-zinc-800 space-y-2 bg-[#18181b]">
              <div className="w-8 h-8 rounded-lg bg-[#da7756]/15 border border-[#da7756]/25 text-[#da7756] flex items-center justify-center">
                <Icon className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white">{spec.role}</h4>
                <span className="text-[10px] text-[#da7756] font-semibold block">{spec.specialty}</span>
                <p className="text-[11px] text-zinc-400 leading-relaxed pt-1">{spec.summary}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Filter Tabs & Active Roster */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-300">
              Active Agent Nodes ({agents.length})
            </span>
          </div>

          <div className="flex items-center gap-2">
            {[
              { id: "all", label: "All Nodes" },
              { id: "thinking", label: "Thinking" },
              { id: "idle", label: "Idle" },
              { id: "completed", label: "Completed" }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setFilter(tab.id)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition cursor-pointer ${
                  filter === tab.id
                    ? "bg-[#da7756]/15 text-white border border-[#da7756]/40"
                    : "text-zinc-400 hover:text-white bg-[#18181b] border border-zinc-800"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-48 rounded-2xl bg-[#18181b] border border-zinc-800 animate-pulse" />
            ))}
          </div>
        ) : filteredAgents.length === 0 ? (
          <div className="text-center py-12 text-zinc-500 text-xs italic bg-[#18181b] border border-zinc-800 rounded-2xl">
            No agents found with status "{filter}".
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredAgents.map((agent) => (
              <AgentCard key={agent.name} agent={agent} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
