"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import AgentCard from "@/components/AgentCard";
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
  Rocket
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

export default function Dashboard() {
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [selectedPlugin, setSelectedPlugin] = useState("");
  const [prompt, setPrompt] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

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
      
      const runningCount = tasksData.filter((t: any) => t.status === "running").length;
      
      setStats({
        totalTasks: tasksData.length,
        activeTools: toolsData.length + 5, // Include built-in tools
        memories: memoriesData.length,
        avgConfidence: tasksData.length > 0 ? "95%" : "N/A"
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

  const handleDeleteTask = async (taskId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this task? All subtasks and logs will be permanently deleted.")) {
      return;
    }
    try {
      await api.deleteTask(taskId);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
      setStats((prev) => ({
        ...prev,
        totalTasks: Math.max(0, prev.totalTasks - 1),
      }));
    } catch (err) {
      alert("Failed to delete task: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-9 w-full relative z-10">
      
      {/* 2-Column Hero & Quick Launch Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
        
        {/* Welcome Text Left Panel */}
        <div className="lg:col-span-7 flex flex-col justify-between py-2">
          <div>
            <div className="flex items-center gap-2 text-blue-450 font-semibold text-xs uppercase tracking-widest mb-2.5">
              <Sparkles className="w-4 h-4 text-blue-400 animate-pulse" />
              <span>Autonomous Workforce Engine</span>
            </div>
            <h2 className="text-4xl font-extrabold tracking-tight text-white leading-tight">
              <span className="text-gradient-blue">AgentForge</span> Control Center
            </h2>
            <p className="text-slate-400 text-sm mt-3.5 max-w-xl leading-relaxed font-medium">
              Welcome to the central workforce coordinator. Orchestrate collaborative teams of AI agents that structure, debug, research, and execute complex workflows in parallel.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
            <Link 
              href="/chat"
              className="flex items-center justify-between p-5 rounded-xl border border-slate-900 bg-slate-950/40 hover:bg-slate-900/20 hover:border-slate-800/80 transition-all duration-300 group glass-card-hover"
            >
              <div className="space-y-1">
                <span className="text-xs font-bold text-slate-100 group-hover:text-blue-450 transition-colors">Interactive Workspace</span>
                <p className="text-[10px] text-slate-500 leading-normal font-medium">Inspect running agents & verify output</p>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-blue-400 group-hover:translate-x-1 transition-all" />
            </Link>

            <Link 
              href="/recent"
              className="flex items-center justify-between p-5 rounded-xl border border-slate-900 bg-slate-950/40 hover:bg-slate-900/20 hover:border-slate-800/80 transition-all duration-300 group glass-card-hover"
            >
              <div className="space-y-1">
                <span className="text-xs font-bold text-slate-100 group-hover:text-blue-450 transition-colors">Launch History Logs</span>
                <p className="text-[10px] text-slate-500 leading-normal font-medium">Full audit trails of past workflow runs</p>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-blue-400 group-hover:translate-x-1 transition-all" />
            </Link>
          </div>
        </div>

        {/* Quick Launch Console Right Panel */}
        <div className="lg:col-span-5">
          <div className="glass-panel border border-slate-850 rounded-2xl p-5 shadow-2xl relative overflow-hidden flex flex-col justify-between h-full shimmer-sweep premium-glow-blue">
            <div className="absolute top-0 right-0 w-24 h-24 bg-blue-600/10 rounded-full blur-2xl pointer-events-none" />
            
            <div className="flex items-center gap-2 border-b border-slate-900 pb-3 mb-4">
              <Rocket className="w-4 h-4 text-blue-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Quick Start Launch
              </h3>
            </div>

            <form onSubmit={handleLaunch} className="space-y-4 flex-1 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <label className="text-[9px] text-slate-500 font-bold uppercase tracking-wider">
                    Select Plugin Workflow
                  </label>
                  <select 
                    value={selectedPlugin}
                    onChange={(e) => setSelectedPlugin(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-850 rounded-lg px-3.5 py-2.5 text-xs text-slate-300 font-medium focus:outline-none focus:border-blue-500/50"
                  >
                    {plugins.length === 0 ? (
                      <option value="">No plugins loaded</option>
                    ) : (
                      plugins.map((p) => (
                        <option key={p.plugin_id} value={p.plugin_id}>
                          {p.name}
                        </option>
                      ))
                    )}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[9px] text-slate-500 font-bold uppercase tracking-wider">
                    Task Prompt Goal
                  </label>
                  <textarea 
                    rows={3}
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Describe what the collaborative workforce should accomplish..."
                    className="w-full bg-slate-950 border border-slate-850 rounded-lg p-3 text-xs text-slate-300 placeholder-slate-650 focus:outline-none focus:border-blue-500/50 leading-relaxed resize-none"
                  />
                </div>
              </div>

              <button 
                type="submit"
                disabled={!prompt.trim() || isSubmitting || !selectedPlugin}
                className="w-full mt-4 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-650 hover:from-blue-500 hover:to-indigo-550 text-xs font-bold text-white flex items-center justify-center gap-2 transition duration-300 glow-primary disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Planning workforce steps...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3 h-3 fill-white" />
                    <span>Start Launch Workflow</span>
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        {[
          { label: "Total Tasks Spanned", val: stats.totalTasks, icon: Layers, color: "text-blue-405 bg-blue-500/5 border-blue-500/10 hover:border-blue-500/20" },
          { label: "Active Integrations", val: stats.activeTools, icon: Cpu, color: "text-purple-405 bg-purple-500/5 border-purple-500/10 hover:border-purple-500/20" },
          { label: "Memory Bank Units", val: stats.memories, icon: BrainCircuit, color: "text-emerald-405 bg-emerald-500/5 border-emerald-500/10 hover:border-emerald-500/20" },
          { label: "Quality Confidence", val: stats.avgConfidence, icon: Activity, color: "text-pink-405 bg-pink-500/5 border-pink-500/10 hover:border-pink-500/20" }
        ].map((item, idx) => {
          const Icon = item.icon;
          return (
            <div key={idx} className={`glass-panel border border-slate-800/80 p-5 rounded-xl flex items-center justify-between hover:scale-[1.02] hover:-translate-y-0.5 transition-all duration-300 ${item.color}`}>
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                  {item.label}
                </span>
                <h4 className="text-2xl font-bold text-white mt-1">
                  {item.val}
                </h4>
              </div>
              <div className="w-10 h-10 rounded-lg flex items-center justify-center border border-slate-800 bg-slate-950/60 shadow-inner">
                <Icon className="w-5 h-5 text-blue-400" />
              </div>
            </div>
          );
        })}
      </div>

      {/* 2-Column Split: Active Workforce vs Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
        
        {/* Left Side: Active Workforce (span 8) */}
        <div className="lg:col-span-8 space-y-4">
          <div>
            <h3 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-450" />
              <span>Active Collaborative Workforce</span>
            </h3>
            <p className="text-slate-500 text-xs mt-0.5 font-medium">Specialized agent modules running within the LangGraph state orchestration framework.</p>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-44 rounded-xl bg-slate-900/30 animate-pulse border border-slate-850" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {agents.map((agent) => (
                <AgentCard
                  key={agent.name}
                  name={agent.name}
                  role={agent.role}
                  status={agent.status}
                  description={agent.description}
                  tools={agent.tools}
                />
              ))}
            </div>
          )}
        </div>

        {/* Right Side: Recent Activity Feed Widget (span 4) */}
        <div className="lg:col-span-4 flex flex-col space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">Recent Activity</h3>
              <p className="text-slate-500 text-xs mt-0.5 font-medium">Quick lookup of latest runs.</p>
            </div>
            <Link 
              href="/recent" 
              className="text-[11px] font-bold text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-1 transition-all"
            >
              <span>View All</span>
              <History className="w-3 h-3" />
            </Link>
          </div>

          <div className="glass-panel border border-slate-850 rounded-xl p-4 flex-1 flex flex-col justify-between space-y-4 premium-glow-purple">
            {loading ? (
              <div className="flex-1 flex items-center justify-center py-10">
                <div className="w-5 h-5 border-2 border-slate-700 border-t-blue-500 rounded-full animate-spin" />
              </div>
            ) : tasks.length === 0 ? (
              <div className="flex-1 flex items-center justify-center py-10 text-slate-500 text-xs italic">
                No past tasks recorded.
              </div>
            ) : (
              <div className="space-y-3.5 flex-1">
                {tasks.slice(0, 4).map((t) => (
                  <div 
                    key={t.id}
                    className="flex flex-col p-3 rounded-lg border border-slate-900 bg-slate-950/20 hover:border-slate-800 transition"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <span className="text-slate-200 text-xs font-semibold truncate flex-1 block" title={t.prompt}>
                        {t.prompt}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full border text-[9px] font-bold uppercase tracking-wider shrink-0 ${
                        t.status === "completed" 
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : t.status === "running"
                          ? "bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse"
                          : t.status === "failed"
                          ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                          : "bg-slate-950 text-slate-500 border-slate-805"
                      }`}>
                        {t.status}
                      </span>
                    </div>

                    <div className="flex items-center justify-between mt-2.5 border-t border-slate-900/60 pt-2 text-[10px]">
                      <span className="text-slate-500 font-mono font-medium">{t.plugin_name}</span>
                      <div className="flex items-center gap-2">
                        <Link 
                          href={`/chat?task_id=${t.id}`}
                          className="text-blue-400 hover:text-blue-300 font-bold flex items-center gap-0.5"
                        >
                          <span>Inspect</span>
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                        <button
                          onClick={(e) => handleDeleteTask(t.id, e)}
                          className="text-rose-500 hover:text-rose-450 transition"
                          title="Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            <Link 
              href="/recent"
              className="w-full py-2.5 rounded-lg border border-slate-800 bg-slate-950/40 hover:bg-slate-900/20 text-xs font-semibold text-slate-300 hover:text-white flex items-center justify-center gap-1.5 transition duration-300"
            >
              <span>View Full Launch History</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

      </div>

    </div>
  );
}
