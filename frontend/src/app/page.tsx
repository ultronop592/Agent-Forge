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
  AlertCircle
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
  { label: "AI Developer Jobs in India", prompt: "Give me the AI Developer roles jobs posted today in India with salary ranges and direct URLs" },
  { label: "High-Performance FastAPI Cache", prompt: "Implement a thread-safe Redis token bucket rate limiter in Python with SOLID principles" },
  { label: "Autonomous Agent Market Report", prompt: "Conduct market intelligence and competitive SWOT analysis for autonomous multi-agent orchestration frameworks" },
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
    <div className="p-8 max-w-7xl mx-auto space-y-9 w-full relative z-10">
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
        description="Are you sure you want to permanently delete this task? All subtasks, logs, and outputs will be erased."
        itemLabel={taskToDelete?.prompt}
        itemSubLabel={taskToDelete ? `Plugin: ${taskToDelete.plugin_name} • ID: ${taskToDelete.id}` : undefined}
        confirmText="Delete Task"
        isLoading={isDeleting}
        errorMessage={deleteError}
      />

      {/* 2-Column Hero & Quick Launch Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
        {/* Welcome Text Left Panel */}
        <div className="lg:col-span-7 flex flex-col justify-between py-1">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-500/10 border border-sky-500/30 text-sky-400 font-semibold text-xs uppercase tracking-widest">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Multi-Agent Autonomous Orchestration</span>
            </div>
            <h2 className="text-4xl font-extrabold tracking-tight text-white leading-tight">
              Orchestrate High-Performance <br />
              <span className="text-gradient-ice">AI Workforce Workflows</span>
            </h2>
            <p className="text-slate-400 text-sm leading-relaxed max-w-xl">
              Decompose complex goals into targeted subtasks. Specialized autonomous agents search the live web, synthesize code, reason through tradeoffs, and verify deliverable quality in real time.
            </p>
          </div>

          {/* Quick Preset Buttons */}
          <div className="pt-6 space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
              Quick Launch Inspiration
            </span>
            <div className="flex flex-wrap gap-2">
              {PRESET_GOALS.map((preset, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setPrompt(preset.prompt)}
                  className="px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300 hover:text-sky-300 hover:border-sky-500/40 text-xs font-medium transition cursor-pointer text-left"
                >
                  ⚡ {preset.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Quick Launch Card Right Panel */}
        <div className="lg:col-span-5">
          <form onSubmit={handleLaunch} className="glass-panel-elevated rounded-2xl p-6 flex flex-col justify-between h-full space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-sky-500/20 text-sky-400 flex items-center justify-center">
                  <Rocket className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-sm text-white">Deploy New Workspace</h3>
              </div>
              <span className="text-[10px] font-bold uppercase text-slate-400 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded-md">
                Reactive HITL
              </span>
            </div>

            <div className="space-y-3.5 flex-1">
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Target Objective / Goal
                </label>
                <textarea
                  rows={3}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe your goal (e.g. 'Search and aggregate today's AI developer jobs in India' or 'Build a rate limiter in Python')..."
                  className="w-full bg-[#080b12] border border-slate-800 rounded-xl p-3.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500/60 focus:ring-1 focus:ring-sky-500/30 transition resize-none leading-relaxed"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Workflow Orchestration Plugin
                </label>
                <select
                  value={selectedPlugin}
                  onChange={(e) => setSelectedPlugin(e.target.value)}
                  className="w-full bg-[#080b12] border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500/60 transition cursor-pointer"
                >
                  {plugins.map((p) => (
                    <option key={p.plugin_id} value={p.plugin_id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !prompt.trim()}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-sky-950/50 disabled:opacity-50 transition-all cursor-pointer glow-primary"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Initializing Workforce Graph...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-white" />
                  <span>Initialize & Deploy Workspace</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Tasks Orchestrated", val: stats.totalTasks, icon: Layers, color: "text-sky-400", bg: "bg-sky-500/10 border-sky-500/20" },
          { label: "Active Capabilities / Tools", val: stats.activeTools, icon: Cpu, color: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/20" },
          { label: "Semantic Memories Recalled", val: stats.memories, icon: BrainCircuit, color: "text-indigo-400", bg: "bg-indigo-500/10 border-indigo-500/20" },
          { label: "QA Confidence Rating", val: stats.avgConfidence, icon: ShieldCheck, color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
        ].map((item, idx) => {
          const Icon = item.icon;
          return (
            <div key={idx} className="glass-panel rounded-2xl p-5 border border-slate-800/80 hover:border-slate-700 transition flex items-center justify-between">
              <div className="space-y-1">
                <span className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">
                  {item.label}
                </span>
                <h4 className="text-2xl font-extrabold text-white tracking-tight">
                  {item.val}
                </h4>
              </div>
              <div className={`w-11 h-11 rounded-xl flex items-center justify-center border ${item.bg}`}>
                <Icon className={`w-5 h-5 ${item.color}`} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Agent Roster Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-white tracking-tight">
              Autonomous Agent Workforce Roster
            </h3>
            <p className="text-xs text-slate-400">
              Specialized LLM agent nodes configured with tool capabilities, token budgets, and verification gates.
            </p>
          </div>
          <span className="text-[11px] font-semibold text-sky-400 bg-sky-500/10 border border-sky-500/20 px-2.5 py-1 rounded-lg">
            {agents.length} Active Nodes
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {loading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-40 rounded-2xl bg-slate-900/40 border border-slate-800/60 animate-pulse" />
            ))
          ) : (
            agents.map((agent) => (
              <AgentCard key={agent.name} agent={agent} />
            ))
          )}
        </div>
      </div>

      {/* Recent Deployments Table */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-sky-400" />
            <h3 className="font-bold text-sm text-white">Recent Workforce Launches</h3>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Filter recent runs..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="bg-[#080b12] border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500/60 w-48 sm:w-64"
              />
            </div>
            <Link
              href="/recent"
              className="text-xs font-semibold text-sky-400 hover:text-sky-300 hover:underline flex items-center gap-1 shrink-0"
            >
              <span>View Audit Trail</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        {tasks.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs italic">
            No workspaces launched yet. Launch your first autonomous workforce goal above.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800/80 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="pb-3 pl-2">Objective / Prompt</th>
                  <th className="pb-3">Plugin</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3">Launched</th>
                  <th className="pb-3 text-right pr-2">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {filteredTasks.slice(0, 5).map((t) => (
                  <tr key={t.id} className="hover:bg-slate-900/40 transition group">
                    <td className="py-3 pl-2 font-medium text-slate-200 max-w-md truncate" title={t.prompt}>
                      {t.prompt}
                    </td>
                    <td className="py-3 text-slate-400 font-mono text-[11px]">
                      {t.plugin_name}
                    </td>
                    <td className="py-3">
                      <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wider ${
                        t.status === "completed"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : t.status === "running"
                          ? "bg-sky-500/10 text-sky-400 border-sky-500/20 animate-pulse"
                          : t.status === "failed"
                          ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                          : "bg-slate-900 text-slate-500 border-slate-800"
                      }`}>
                        {t.status}
                      </span>
                    </td>
                    <td className="py-3 text-slate-500 text-[11px]">
                      {new Date(t.created_at).toLocaleDateString()} {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-3 text-right pr-2">
                      <div className="flex items-center justify-end gap-3">
                        <Link
                          href={`/chat?task_id=${t.id}`}
                          className="text-sky-400 hover:text-sky-300 font-semibold inline-flex items-center gap-1 group-hover:underline"
                        >
                          <span>Inspect</span>
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                        <button
                          onClick={(e) => handleRequestDelete(t, e)}
                          className="text-slate-500 hover:text-rose-400 p-1 hover:bg-rose-500/10 rounded transition cursor-pointer"
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
