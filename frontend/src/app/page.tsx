"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import AgentCard from "@/components/AgentCard";
import DeleteConfirmModal from "@/components/DeleteConfirmModal";
import { 
  Play, 
  Layers, 
  Activity, 
  BrainCircuit, 
  Cpu, 
  ArrowRight,
  Sparkles,
  History,
  Trash2,
  Rocket,
  ShieldCheck,
  Zap,
  Search,
  CheckCircle2,
  Clock,
  Compass,
  FileCode,
  FolderGit,
  HelpCircle,
  CheckCircle,
  ExternalLink,
  ChevronRight
} from "lucide-react";

interface Agent {
  name: string;
  role: string;
  status: "idle" | "thinking" | "tool_call" | "completed" | "failed";
  description: string;
  tools: string[];
}

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

const PRESET_GOALS = [
  { 
    label: "AI Engineer Jobs in India", 
    prompt: "Search and aggregate AI Developer job openings posted today in India with salary estimates and direct URLs." 
  },
  { 
    label: "Python Redis Rate Limiter", 
    prompt: "Implement a thread-safe Redis token bucket rate limiter in Python adhering to SOLID design principles." 
  },
  { 
    label: "Autonomous Multi-Agent SWOT", 
    prompt: "Perform market intelligence and competitive SWOT analysis for autonomous multi-agent orchestration frameworks." 
  },
];

const ARCHITECTURE_STEPS = [
  {
    step: "01",
    title: "Goal Decomposition",
    agent: "Planner Agent",
    icon: Compass,
    description: "Analyzes your prompt, outlines critical constraints, and breaks it down into logical sequential subtasks with Human-in-the-Loop approval."
  },
  {
    step: "02",
    title: "Live Web Grounding",
    agent: "Analyst & Researcher",
    icon: Search,
    description: "Searches the live web via Tavily & DuckDuckGo, gathering verified data and real URLs with zero fake hallucinated links."
  },
  {
    step: "03",
    title: "Code & Report Synthesis",
    agent: "Executor Agent",
    icon: FileCode,
    description: "Transforms researched context into clean deliverables — production-ready code, markdown tables, or strategic roadmaps."
  },
  {
    step: "04",
    title: "QA Verification & Memory",
    agent: "Verifier & Memory",
    icon: ShieldCheck,
    description: "Evaluates factual accuracy, removes ungrounded claims, scores confidence (95%+), and records insights to the Vector Memory Bank."
  }
];

export default function Dashboard() {
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [selectedPlugin, setSelectedPlugin] = useState("");
  const [prompt, setPrompt] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [searchFilter, setSearchFilter] = useState("");

  const [taskToDelete, setTaskToDelete] = useState<Task | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const [stats, setStats] = useState({
    totalTasks: 0,
    activeTools: 0,
    memories: 0,
    avgConfidence: "95%"
  });
  const [loading, setLoading] = useState(true);

  const loadDashboardData = async () => {
    try {
      const [agentsData, tasksData, memoriesData, toolsData, pluginsData] = await Promise.all([
        api.getAgents(),
        api.getTasks(),
        api.getMemory(),
        api.getMCPTools().catch(() => []),
        api.getPlugins().catch(() => [])
      ]);

      setAgents(agentsData);
      setTasks(tasksData);
      setPlugins(pluginsData);
      
      if (pluginsData.length > 0) {
        setSelectedPlugin((prev) => prev || pluginsData[0].plugin_id);
      }
      
      const completedTasks = tasksData.filter((t: any) => t.status === "completed" && (t.confidence_score || 0) > 0);
      const computedAvg = completedTasks.length > 0
        ? Math.round((completedTasks.reduce((acc: number, cur: any) => acc + (cur.confidence_score || 0), 0) / completedTasks.length) * 100) + "%"
        : tasksData.length > 0 ? "95%" : "N/A";
      
      setStats({
        totalTasks: tasksData.length,
        activeTools: toolsData.length + 5,
        memories: memoriesData.length,
        avgConfidence: computedAvg
      });

    } catch (e) {
      console.error("Dashboard data load error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 8000);
    return () => clearInterval(interval);
  }, []);

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

  const handleRequestDelete = (task: Task, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDeleteError(null);
    setTaskToDelete(task);
  };

  const handleConfirmDelete = async () => {
    if (!taskToDelete) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteTask(taskToDelete.id);
      setTasks((prev) => prev.filter((t) => t.id !== taskToDelete.id));
      setStats((prev) => ({
        ...prev,
        totalTasks: Math.max(0, prev.totalTasks - 1),
      }));
      setTaskToDelete(null);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsDeleting(false);
    }
  };

  const filteredTasks = tasks.filter(t => 
    t.prompt.toLowerCase().includes(searchFilter.toLowerCase()) ||
    t.plugin_name.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-10 w-full relative z-10 bg-[#121214] text-[#f4f4f5]">
      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={!!taskToDelete}
        onClose={() => {
          if (!isDeleting) {
            setTaskToDelete(null);
            setDeleteError(null);
          }
        }}
        onConfirm={handleConfirmDelete}
        title="Delete Workforce Task"
        description="Are you sure you want to delete this task? All subtasks, logs, and verified reports will be removed."
        itemLabel={taskToDelete?.prompt}
        itemSubLabel={taskToDelete ? `Plugin: ${taskToDelete.plugin_name} • ID: ${taskToDelete.id}` : undefined}
        confirmText="Delete Task"
        isLoading={isDeleting}
        errorMessage={deleteError}
      />

      {/* 1. Project Explanation & Quick Launch Hero */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
        
        {/* What is AgentForge? Explanation */}
        <div className="lg:col-span-7 flex flex-col justify-between space-y-6">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#da7756]/10 border border-[#da7756]/30 text-[#da7756] text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Autonomous AI Workforce Platform</span>
            </div>

            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white leading-tight">
              Collaborative AI Agents for <br />
              <span className="text-[#da7756]">Complex, Real-World Objectives</span>
            </h1>

            <p className="text-zinc-300 text-sm leading-relaxed max-w-2xl">
              <strong>AgentForge</strong> is an autonomous multi-agent orchestration platform. Instead of a single generic chatbot, AgentForge deploys a specialized team of AI agents that collaboratively plan, research live web data, write software, synthesize reports, and rigorously fact-check every output before delivery.
            </p>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="p-3.5 rounded-xl bg-[#18181b] border border-zinc-800 space-y-1">
                <div className="flex items-center gap-2 text-[#da7756] text-xs font-bold">
                  <CheckCircle className="w-3.5 h-3.5 text-[#da7756]" />
                  <span>Real Live Search Grounding</span>
                </div>
                <p className="text-[11px] text-zinc-400 leading-normal">
                  Crawls live sources with automatic verification — no fabricated links.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-[#18181b] border border-zinc-800 space-y-1">
                <div className="flex items-center gap-2 text-[#da7756] text-xs font-bold">
                  <CheckCircle className="w-3.5 h-3.5 text-[#da7756]" />
                  <span>LLM-as-Judge QA Gates</span>
                </div>
                <p className="text-[11px] text-zinc-400 leading-normal">
                  Automated verification scores faithfulness and technical quality.
                </p>
              </div>
            </div>
          </div>

          {/* Quick Preset Buttons */}
          <div className="space-y-2 pt-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 block">
              Try A Sample Objective:
            </span>
            <div className="flex flex-wrap gap-2">
              {PRESET_GOALS.map((preset, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setPrompt(preset.prompt)}
                  className="px-3 py-1.5 rounded-lg bg-[#18181b] border border-zinc-800 text-zinc-300 hover:text-white hover:border-[#da7756]/50 text-xs font-medium transition cursor-pointer text-left"
                >
                  💡 {preset.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Clean, Minimal Goal Dispatcher Card */}
        <div className="lg:col-span-5">
          <form onSubmit={handleLaunch} className="glass-panel rounded-2xl p-6 flex flex-col justify-between h-full space-y-5 border border-zinc-800 bg-[#18181b]">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3.5">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-[#da7756]/15 border border-[#da7756]/30 text-[#da7756] flex items-center justify-center">
                  <Rocket className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-sm text-white">Deploy AI Workforce</h3>
              </div>
              <span className="text-[10px] font-semibold text-zinc-400 bg-[#121214] border border-zinc-800 px-2 py-0.5 rounded">
                HITL Enabled
              </span>
            </div>

            <div className="space-y-4 flex-1">
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-zinc-300 uppercase tracking-wider">
                  Target Goal / Task Description
                </label>
                <textarea
                  rows={4}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe what you want the workforce to accomplish (e.g. 'Search and aggregate today's AI developer jobs in India' or 'Build a rate limiter in Python')..."
                  className="w-full bg-[#121214] border border-zinc-800 rounded-xl p-3.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#da7756]/70 transition resize-none leading-relaxed"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-zinc-300 uppercase tracking-wider">
                  Workflow Orchestration Blueprint
                </label>
                <select
                  value={selectedPlugin}
                  onChange={(e) => setSelectedPlugin(e.target.value)}
                  className="w-full bg-[#121214] border border-zinc-800 rounded-xl px-3.5 py-2.5 text-xs text-zinc-200 focus:outline-none focus:border-[#da7756]/70 transition cursor-pointer"
                >
                  {plugins.map((p) => (
                    <option key={p.plugin_id} value={p.plugin_id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Clean Minimal Button - Claude Orange & No Glow */}
            <button
              type="submit"
              disabled={isSubmitting || !prompt.trim()}
              className="w-full py-3 rounded-xl bg-[#da7756] hover:bg-[#c96a4a] text-white font-bold text-xs flex items-center justify-center gap-2 disabled:opacity-40 transition-colors cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Planning Workforce Subtasks...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-white" />
                  <span>Deploy Autonomous Workforce</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* 2. How It Works (Step-by-Step Multi-Agent Flow) */}
      <div className="space-y-4 pt-2">
        <div>
          <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
            <Compass className="w-4 h-4 text-[#da7756]" />
            <span>How The AgentForge Workforce Operates</span>
          </h2>
          <p className="text-xs text-zinc-400">
            A deterministic, sequential multi-agent pipeline from raw prompt to verified deliverable.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {ARCHITECTURE_STEPS.map((item, idx) => {
            const Icon = item.icon;
            return (
              <div key={idx} className="glass-panel rounded-2xl p-5 border border-zinc-800 space-y-3 relative overflow-hidden bg-[#18181b]">
                <div className="flex items-center justify-between">
                  <div className="w-8 h-8 rounded-lg bg-[#da7756]/15 border border-[#da7756]/20 text-[#da7756] flex items-center justify-center">
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="text-xs font-mono font-bold text-zinc-500">{item.step}</span>
                </div>

                <div className="space-y-1">
                  <h3 className="text-xs font-bold text-white">{item.title}</h3>
                  <span className="text-[10px] font-semibold text-[#da7756] block">{item.agent}</span>
                  <p className="text-[11px] text-zinc-400 leading-relaxed pt-1">
                    {item.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Live Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Tasks Orchestrated", val: stats.totalTasks, icon: Layers, color: "text-[#da7756]" },
          { label: "Active Capabilities / Tools", val: stats.activeTools, icon: Cpu, color: "text-[#da7756]" },
          { label: "Semantic Memories Recalled", val: stats.memories, icon: BrainCircuit, color: "text-[#da7756]" },
          { label: "QA Confidence Rating", val: stats.avgConfidence, icon: ShieldCheck, color: "text-emerald-400" },
        ].map((item, idx) => {
          const Icon = item.icon;
          return (
            <div key={idx} className="glass-panel rounded-2xl p-5 border border-zinc-800 flex items-center justify-between bg-[#18181b]">
              <div className="space-y-1">
                <span className="text-[10px] font-bold uppercase text-zinc-500 tracking-wider">
                  {item.label}
                </span>
                <h4 className="text-2xl font-extrabold text-white tracking-tight">
                  {item.val}
                </h4>
              </div>
              <div className="w-10 h-10 rounded-xl flex items-center justify-center border border-zinc-800 bg-[#121214]">
                <Icon className={`w-4 h-4 ${item.color}`} />
              </div>
            </div>
          );
        })}
      </div>

      {/* 4. Agent Workforce Roster */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">
              Autonomous Agent Workforce Roster
            </h2>
            <p className="text-xs text-zinc-400">
              Specialized LLM agent nodes configured with tool capabilities, token budgets, and verification gates.
            </p>
          </div>
          <span className="text-[11px] font-semibold text-[#da7756] bg-[#da7756]/10 border border-[#da7756]/20 px-2.5 py-1 rounded-lg">
            {agents.length} Active Nodes
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {loading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-40 rounded-2xl bg-[#18181b] border border-zinc-800 animate-pulse" />
            ))
          ) : (
            agents.map((agent) => (
              <AgentCard key={agent.name} agent={agent} />
            ))
          )}
        </div>
      </div>

      {/* 5. Recent Deployments Table */}
      <div className="glass-panel rounded-2xl p-6 border border-zinc-800 space-y-4 bg-[#18181b]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-[#da7756]" />
            <h3 className="font-bold text-sm text-white">Recent Workforce Launches</h3>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Filter recent runs..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="bg-[#121214] border border-zinc-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-[#da7756]/60 w-48 sm:w-64"
              />
            </div>
            <Link
              href="/recent"
              className="text-xs font-semibold text-[#da7756] hover:text-[#e08569] hover:underline flex items-center gap-1 shrink-0"
            >
              <span>View Audit Trail</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        {tasks.length === 0 ? (
          <div className="text-center py-12 text-zinc-500 text-xs italic">
            No workspaces launched yet. Enter an objective above to start your first run.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                  <th className="pb-3 pl-2">Objective / Prompt</th>
                  <th className="pb-3">Blueprint</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3">Launched</th>
                  <th className="pb-3 text-right pr-2">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {filteredTasks.slice(0, 5).map((t) => (
                  <tr key={t.id} className="hover:bg-zinc-800/40 transition">
                    <td className="py-3 pl-2 font-medium text-zinc-200 max-w-md truncate" title={t.prompt}>
                      {t.prompt}
                    </td>
                    <td className="py-3 text-zinc-400 font-mono text-[11px]">
                      {t.plugin_name}
                    </td>
                    <td className="py-3">
                      <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wider ${
                        t.status === "completed"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : t.status === "running"
                          ? "bg-[#da7756]/10 text-[#da7756] border-[#da7756]/20"
                          : t.status === "failed"
                          ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                          : "bg-zinc-900 text-zinc-500 border-zinc-800"
                      }`}>
                        {t.status}
                      </span>
                    </td>
                    <td className="py-3 text-zinc-400 text-[11px]">
                      {new Date(t.created_at).toLocaleDateString()} {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-3 text-right pr-2">
                      <div className="flex items-center justify-end gap-3">
                        <Link
                          href={`/chat?task_id=${t.id}`}
                          className="text-[#da7756] hover:text-[#e08569] font-semibold inline-flex items-center gap-1"
                        >
                          <span>Inspect</span>
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                        <button
                          onClick={(e) => handleRequestDelete(t, e)}
                          className="text-zinc-500 hover:text-rose-400 p-1 hover:bg-rose-500/10 rounded transition cursor-pointer"
                          title="Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
