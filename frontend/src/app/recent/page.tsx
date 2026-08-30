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

import DeleteConfirmModal from "@/components/DeleteConfirmModal";

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
  const [taskToDelete, setTaskToDelete] = useState<Task | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

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
      setTaskToDelete(null);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsDeleting(false);
    }
  };

  const totalRuns = tasks.length;
  const completedRuns = tasks.filter(t => t.status === "completed").length;
  const runningRuns = tasks.filter(t => t.status === "running").length;
  const failedRuns = tasks.filter(t => t.status === "failed").length;
  const successRate = totalRuns > 0 ? Math.round((completedRuns / (totalRuns - runningRuns || 1)) * 100) : 0;

  const filteredTasks = tasks.filter(t => {
    const matchesSearch = t.prompt.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          t.plugin_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "all" || t.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 w-full relative z-10 bg-[#121214] text-[#f4f4f5]">
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
        title="Delete Launch Record"
        description="Are you sure you want to permanently delete this launch execution? All subtasks, timeline logs, and outputs will be erased."
        itemLabel={taskToDelete?.prompt}
        itemSubLabel={taskToDelete ? `Plugin: ${taskToDelete.plugin_name} • ID: ${taskToDelete.id}` : undefined}
        confirmText="Delete Record"
        isLoading={isDeleting}
        errorMessage={deleteError}
      />

      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-zinc-800 pb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-[#da7756]/15 border border-[#da7756]/30 text-[#da7756] flex items-center justify-center">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-white">
                Workspace Launch History & Audit Trail
              </h2>
              <p className="text-zinc-400 text-xs mt-0.5 max-w-2xl leading-relaxed">
                Review detailed execution records, agent division logs, and verified reports across all workforce launches.
              </p>
            </div>
          </div>
        </div>

        <Link 
          href="/chat"
          className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[#da7756] hover:bg-[#c96a4a] text-white text-xs font-bold transition-colors self-start md:self-center"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Launch New Workspace</span>
        </Link>
      </div>

      {/* Analytics Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Tasks Orchestrated", val: totalRuns, icon: Activity, color: "text-[#da7756] border-[#da7756]/20 bg-[#121214]" },
          { label: "QA Verification Success Rate", val: `${successRate}%`, icon: CheckCircle2, color: "text-emerald-400 border-emerald-500/20 bg-[#121214]" },
          { label: "Active Deployments", val: runningRuns, icon: Loader2, color: "text-amber-400 border-amber-500/20 bg-[#121214]", animate: runningRuns > 0 },
          { label: "Failed Runs", val: failedRuns, icon: XCircle, color: "text-rose-400 border-rose-500/20 bg-[#121214]" }
        ].map((item, idx) => {
          const Icon = item.icon;
          return (
            <div key={idx} className="glass-panel border border-zinc-800 p-5 rounded-2xl flex items-center justify-between hover:border-zinc-700 transition bg-[#18181b]">
              <div className="space-y-1">
                <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">
                  {item.label}
                </span>
                <h4 className="text-2xl font-extrabold text-white tracking-tight">
                  {item.val}
                </h4>
              </div>
              <div className={`w-11 h-11 rounded-xl flex items-center justify-center border ${item.color}`}>
                <Icon className={`w-5 h-5 ${item.animate ? "animate-spin" : ""}`} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Filters Area */}
      <div className="glass-panel border border-zinc-800 rounded-2xl p-4 flex flex-col md:flex-row gap-4 items-center justify-between bg-[#18181b]">
        {/* Search */}
        <div className="relative w-full md:w-96">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-3" />
          <input 
            type="text"
            placeholder="Search by prompt or plugin..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#121214] border border-zinc-800 rounded-xl pl-9 pr-4 py-2.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#da7756]/60 font-medium"
          />
        </div>

        {/* Dropdowns / Filter list */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-end">
          <div className="flex items-center gap-2">
            <ListFilter className="w-4 h-4 text-zinc-500" />
            <span className="text-xs text-zinc-500 font-semibold uppercase tracking-wider">Status:</span>
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#121214] border border-zinc-800 rounded-xl px-3.5 py-2.5 text-xs text-zinc-200 font-medium focus:outline-none focus:border-[#da7756]/60 cursor-pointer"
          >
            <option value="all">All Runs ({tasks.length})</option>
            <option value="completed">Completed</option>
            <option value="running">Running</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
        </div>
      </div>

      {/* Runs Log Panel */}
      <div className="glass-panel border border-zinc-800 rounded-2xl p-6 bg-[#18181b]">
        <div className="overflow-x-auto">
          {loading ? (
            <div className="text-center py-12 flex flex-col items-center gap-2">
              <Loader2 className="w-8 h-8 text-[#da7756] animate-spin" />
              <span className="text-zinc-500 text-xs font-semibold uppercase tracking-wider">Loading history logs...</span>
            </div>
          ) : filteredTasks.length === 0 ? (
            <div className="text-center py-12 text-zinc-500 text-xs italic">
              No matching task executions found in history.
            </div>
          ) : (
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 font-bold uppercase tracking-wider text-[10px]">
                  <th className="pb-3 pl-2">Objective / Prompt</th>
                  <th className="pb-3">Blueprint</th>
                  <th className="pb-3">Launch Date</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3 text-right pr-2">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {filteredTasks.map((t) => (
                  <tr key={t.id} className="hover:bg-zinc-800/40 group transition">
                    <td className="py-3.5 font-medium text-zinc-200 max-w-md truncate pl-2" title={t.prompt}>
                      {t.prompt}
                    </td>
                    <td className="py-3.5 text-zinc-400 font-mono text-[11px]">
                      {t.plugin_name}
                    </td>
                    <td className="py-3.5 text-zinc-500 text-[11px]">
                      {new Date(t.created_at).toLocaleDateString()} {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-3.5">
                      <span className={`px-2.5 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wider ${
                        t.status === "completed" 
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : t.status === "running"
                          ? "bg-[#da7756]/10 text-[#da7756] border-[#da7756]/20 animate-pulse"
                          : t.status === "failed"
                          ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                          : "bg-zinc-900 text-zinc-500 border-zinc-800"
                      }`}>
                        {t.status}
                      </span>
                    </td>
                    <td className="py-3.5 text-right pr-2">
                      <div className="flex items-center justify-end gap-3">
                        <Link 
                          href={`/chat?task_id=${t.id}`}
                          className="text-[#da7756] hover:text-[#e08569] font-semibold group-hover:underline inline-flex items-center gap-1"
                        >
                          <span>Inspect</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                        <button
                          onClick={(e) => handleRequestDelete(t, e)}
                          className="text-zinc-500 hover:text-rose-400 transition p-1 hover:bg-rose-500/10 rounded cursor-pointer"
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
