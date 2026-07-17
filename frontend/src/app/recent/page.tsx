"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { 
  ArrowRight, 
  Search, 
  Trash2, 
  History, 
  Sparkles, 
  Activity, 
  CheckCircle2, 
  XCircle, 
  Loader2,
  ListFilter
} from "lucide-react";

interface Task {
  id: string;
  prompt: string;
  status: "pending" | "running" | "completed" | "failed";
  plugin_name: string;
  created_at: string;
}

export default function LaunchHistory() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const loadTasks = async () => {
    try {
      const data = await api.getTasks();
      setTasks(data);
    } catch (e) {
      console.error("Failed to load tasks history:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
    const interval = setInterval(loadTasks, 8000);
    return () => clearInterval(interval);
  }, []);

  const handleDeleteTask = async (taskId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this task? All subtasks and logs will be permanently deleted.")) {
      return;
    }
    try {
      await api.deleteTask(taskId);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
    } catch (err) {
      alert("Failed to delete task: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  // Compute metrics
  const totalRuns = tasks.length;
  const completedRuns = tasks.filter(t => t.status === "completed").length;
  const runningRuns = tasks.filter(t => t.status === "running").length;
  const failedRuns = tasks.filter(t => t.status === "failed").length;
  const successRate = totalRuns > 0 ? Math.round((completedRuns / (totalRuns - runningRuns || 1)) * 100) : 0;

  // Filter tasks
  const filteredTasks = tasks.filter(t => {
    const matchesSearch = t.prompt.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          t.plugin_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "all" || t.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 w-full relative z-10">
      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-slate-900 pb-6">
        <div>
          <div className="flex items-center gap-2 text-blue-500 font-semibold text-xs uppercase tracking-widest mb-1.5">
            <History className="w-3.5 h-3.5" />
            <span>Audit Trail & Runs</span>
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-white">
            Workspace Launch History
          </h2>
          <p className="text-slate-400 text-sm mt-1 max-w-2xl leading-relaxed">
            Review detailed execution logs, status history, and verify agent outputs across all past workforce launches.
          </p>
        </div>

        <Link 
          href="/chat"
          className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-semibold transition-all duration-300 shadow-lg glow-primary self-start md:self-center"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Launch New Workspace</span>
        </Link>
      </div>

      {/* Analytics Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        {[
          { label: "Total Runs Orchestrated", val: totalRuns, icon: Activity, color: "text-blue-450 bg-blue-500/5 border-blue-500/10 hover:border-blue-500/20" },
          { label: "Success Rate (Completed)", val: `${successRate}%`, icon: CheckCircle2, color: "text-emerald-450 bg-emerald-500/5 border-emerald-500/10 hover:border-emerald-500/20" },
          { label: "Active Deployments", val: runningRuns, icon: Loader2, color: "text-purple-450 bg-purple-500/5 border-purple-500/10 hover:border-purple-500/20", animate: runningRuns > 0 },
          { label: "Failed Runs", val: failedRuns, icon: XCircle, color: "text-rose-405 bg-rose-500/5 border-rose-500/10 hover:border-rose-500/20" }
        ].map((item, idx) => {
          const Icon = item.icon;
          return (
            <div key={idx} className={`glass-panel border p-5 rounded-xl flex items-center justify-between hover:scale-[1.02] hover:-translate-y-0.5 transition-all duration-305 ${item.color}`}>
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                  {item.label}
                </span>
                <h4 className="text-2xl font-bold text-white mt-1">
                  {item.val}
                </h4>
              </div>
              <div className="w-10 h-10 rounded-lg flex items-center justify-center border border-slate-800 bg-slate-950/60 shadow-inner">
                <Icon className={`w-5 h-5 text-blue-400 ${item.animate ? "animate-spin" : ""}`} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Filters Area */}
      <div className="glass-panel border border-slate-800/80 rounded-xl p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
        {/* Search */}
        <div className="relative w-full md:w-96">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <input 
            type="text"
            placeholder="Search by prompt or plugin..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800/80 rounded-lg pl-9 pr-4 py-2.5 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-blue-500/60 font-medium"
          />
        </div>

        {/* Dropdowns / Filter list */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-end">
          <div className="flex items-center gap-2">
            <ListFilter className="w-4 h-4 text-slate-500" />
            <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Status:</span>
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800/80 rounded-lg px-3.5 py-2.5 text-xs text-slate-300 font-medium focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Runs</option>
            <option value="completed">Completed</option>
            <option value="running">Running</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
        </div>
      </div>

      {/* Runs Log Panel */}
      <div className="glass-panel border border-slate-800/80 rounded-xl p-6">
        <div className="overflow-x-auto">
          {loading ? (
            <div className="text-center py-12 flex flex-col items-center gap-2">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
              <span className="text-slate-500 text-xs font-semibold uppercase tracking-wider">Loading history logs...</span>
            </div>
          ) : filteredTasks.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-xs italic">
              No matching task executions found in history.
            </div>
          ) : (
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-900 text-slate-500 font-bold uppercase tracking-wider">
                  <th className="pb-3 pl-2">Task prompt / Goal</th>
                  <th className="pb-3">Selected Plugin</th>
                  <th className="pb-3">Launch Date</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3 text-right pr-2">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-900/60">
                {filteredTasks.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-900/10 group transition-all">
                    <td className="py-4 font-medium text-slate-200 max-w-lg truncate pl-2" title={t.prompt}>
                      {t.prompt}
                    </td>
                    <td className="py-4 text-slate-400 font-mono text-[11px]">
                      {t.plugin_name}
                    </td>
                    <td className="py-4 text-slate-500">
                      {new Date(t.created_at).toLocaleString()}
                    </td>
                    <td className="py-4">
                      <span className={`px-2.5 py-0.5 rounded-full border text-[10px] font-semibold uppercase tracking-wider ${
                        t.status === "completed" 
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : t.status === "running"
                          ? "bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse"
                          : t.status === "failed"
                          ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                          : "bg-slate-950 text-slate-500 border-slate-800"
                      }`}>
                        {t.status}
                      </span>
                    </td>
                    <td className="py-4 text-right pr-2">
                      <div className="flex items-center justify-end gap-3">
                        <Link 
                          href={`/chat?task_id=${t.id}`}
                          className="text-blue-400 hover:text-blue-300 font-semibold group-hover:underline inline-flex items-center gap-1"
                        >
                          <span>Inspect</span>
                          <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                        </Link>
                        <button
                          onClick={(e) => handleDeleteTask(t.id, e)}
                          className="text-rose-500 hover:text-rose-400 transition p-1 hover:bg-rose-500/10 rounded cursor-pointer"
                          title="Delete Launch"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
