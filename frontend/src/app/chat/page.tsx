"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import WorkflowGraph from "@/components/WorkflowGraph";
import Timeline from "@/components/Timeline";
import AgentTerminal from "@/components/AgentTerminal";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import { 
  Play, 
  Layers, 
  BrainCircuit, 
  Terminal as TermIcon, 
  Sparkles, 
  CheckCircle,
  FileDown,
  RefreshCcw,
  ListTodo,
  Trash2
} from "lucide-react";

interface Subtask {
  id: string;
  task_id: string;
  title: string;
  description: string;
  assigned_agent: string;
  status: "pending" | "running" | "completed" | "failed";
  output?: string;
  confidence_score: number;
}

interface LogEntry {
  id: number;
  task_id: string;
  agent_name: string;
  log_type: string;
  content: string;
  created_at: string;
}

interface Plugin {
  plugin_id: string;
  name: string;
  description: string;
}

function WorkspaceInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const targetTaskId = searchParams.get("task_id");

  const [prompt, setPrompt] = useState("");
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [selectedPlugin, setSelectedPlugin] = useState("");
  const [taskId, setTaskId] = useState<string | null>(null);
  
  // Running state
  const [taskStatus, setTaskStatus] = useState<string>("idle");
  const [subtasks, setSubtasks] = useState<Subtask[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [finalResult, setFinalResult] = useState<string>("");
  const [confidenceScore, setConfidenceScore] = useState<number | null>(null);
  
  // UI Panels Tabs
  const [activeTab, setActiveTab] = useState<"graph" | "timeline" | "terminal" | "result">("graph");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load plugins list on mount
  useEffect(() => {
    const loadPlugins = async () => {
      try {
        const data = await api.getPlugins();
        setPlugins(data);
        if (data.length > 0) {
          setSelectedPlugin(data[0].plugin_id);
        }
      } catch (e) {
        console.error("Failed to load plugins:", e);
      }
    };
    loadPlugins();
  }, []);

  // Inspect task if task_id query is present
  useEffect(() => {
    if (targetTaskId) {
      loadHistoricTask(targetTaskId);
    } else {
      resetWorkspace();
    }
    return () => disconnectStream();
  }, [targetTaskId]);

  const resetWorkspace = () => {
    setTaskId(null);
    setTaskStatus("idle");
    setSubtasks([]);
    setLogs([]);
    setFinalResult("");
    setConfidenceScore(null);
    setActiveTab("graph");
    setIsStreaming(false);
    reconnectAttemptsRef.current = 0;
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
  };

  const loadHistoricTask = async (id: string) => {
    try {
      setTaskId(id);
      const taskData = await api.getTask(id);
      const logsData = await api.getLogs(id);
      
      setPrompt(taskData.prompt);
      setSelectedPlugin(taskData.plugin_name);
      setTaskStatus(taskData.status);
      setFinalResult(taskData.final_result || "");
      setSubtasks(taskData.subtasks || []);
      setLogs(logsData || []);
      
      // Look for verifier subtask score
      const verifierSub = (taskData.subtasks || []).find((s: Subtask) => s.assigned_agent === "verifier");
      if (verifierSub) {
        setConfidenceScore(verifierSub.confidence_score || 0.95);
      }

      if (taskData.status === "running") {
        connectStream(id);
      } else {
        setActiveTab(taskData.status === "completed" ? "result" : "graph");
      }
    } catch (e) {
      console.error("Error loading task detail:", e);
    }
  };

  const MAX_RECONNECT_ATTEMPTS = 5;

  const connectStream = (id: string, attempt = 0) => {
    // Close any existing connection first
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    const streamUrl = api.getStreamUrl(id);
    const es = new EventSource(streamUrl);
    eventSourceRef.current = es;
    reconnectAttemptsRef.current = attempt;

    es.onopen = () => {
      // Reset reconnect counter on successful connect
      reconnectAttemptsRef.current = 0;
      setIsStreaming(true);
    };

    es.onmessage = (event) => {
      try {
        const update = JSON.parse(event.data);

        // Ignore heartbeat comments — browser EventSource filters `: ping` automatically
        // but guard against empty payloads just in case
        if (!update || update.error) {
          if (update?.error) console.error("SSE stream error:", update.error);
          return;
        }

        // Backend signals clean completion
        if (update.done) {
          setIsStreaming(false);
          if (update.status === "completed") setActiveTab("result");
          disconnectStream();
          return;
        }

        if (update.status) setTaskStatus(update.status);
        if (update.final_result) setFinalResult(update.final_result);
        if (update.subtasks)     setSubtasks(update.subtasks);

        if (update.new_logs && update.new_logs.length > 0) {
          // Auto-switch to terminal tab the first time logs arrive
          setActiveTab((prev) => prev === "graph" || prev === "timeline" ? "terminal" : prev);

          setLogs((prev) => {
            const existingIds = new Set(prev.map((l) => l.id));
            const freshLogs = update.new_logs.filter((l: LogEntry) => !existingIds.has(l.id));
            return [...prev, ...freshLogs];
          });
        }

        const verifierSub = (update.subtasks || []).find(
          (s: Subtask) => s.assigned_agent === "verifier"
        );
        if (verifierSub?.confidence_score) {
          setConfidenceScore(verifierSub.confidence_score);
        }

        // Handle terminal states (in case done event is missed)
        if (update.status === "completed") {
          setIsStreaming(false);
          setActiveTab("result");
          disconnectStream();
        } else if (update.status === "failed") {
          setIsStreaming(false);
          disconnectStream();
        }
      } catch (err) {
        console.error("Failed to parse SSE payload:", err);
      }
    };

    es.onerror = () => {
      // Don't reconnect if task is already done or max retries reached
      es.close();
      eventSourceRef.current = null;
      setIsStreaming(false);

      const nextAttempt = attempt + 1;
      if (nextAttempt <= MAX_RECONNECT_ATTEMPTS) {
        const backoffMs = Math.min(1000 * Math.pow(2, attempt), 16000); // 1s,2s,4s,8s,16s
        console.warn(`SSE disconnected. Reconnecting in ${backoffMs}ms (attempt ${nextAttempt}/${MAX_RECONNECT_ATTEMPTS})...`);
        reconnectTimerRef.current = setTimeout(() => {
          // Only reconnect if task is still running
          setTaskStatus((currentStatus) => {
            if (currentStatus === "running" || currentStatus === "pending") {
              connectStream(id, nextAttempt);
            }
            return currentStatus;
          });
        }, backoffMs);
      } else {
        console.error("SSE max reconnect attempts reached. Stopping auto-reconnect.");
      }
    };
  };

  const disconnectStream = () => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsStreaming(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isSubmitting) return;

    setIsSubmitting(true);
    resetWorkspace();
    
    try {
      const task = await api.createTask(prompt, selectedPlugin);
      router.push(`/chat?task_id=${task.id}`);
    } catch (err) {
      console.error("Task creation failed:", err);
      setIsSubmitting(false);
    }
  };

  const downloadResult = () => {
    if (!finalResult) return;
    const blob = new Blob([finalResult], { type: "text/markdown;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `agentforge_report_${taskId}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDelete = async () => {
    if (!taskId) return;
    if (!confirm("Are you sure you want to delete this task? All subtasks and logs will be permanently deleted.")) {
      return;
    }
    setIsDeleting(true);
    try {
      await api.deleteTask(taskId);
      router.push("/chat");
    } catch (err) {
      alert("Failed to delete task: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full min-h-screen relative z-10">
      {/* Upper Navigation Header */}
      <div className="border-b border-slate-900 bg-slate-950/40 p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-blue-500" />
            <span>AI Workforce Workspace</span>
          </h2>
          <p className="text-[11px] text-slate-500 font-medium">
            Deploy workflows, review tasks division, observe thinking, and export results.
          </p>
        </div>

        {taskId && (
          <div className="flex items-center gap-3">
            <button 
              onClick={() => router.push("/chat")}
              className="px-3 py-1.5 rounded bg-slate-900 hover:bg-slate-800 text-[11px] text-slate-300 font-semibold border border-slate-800 flex items-center gap-1.5 transition cursor-pointer"
            >
              <RefreshCcw className="w-3.5 h-3.5" />
              <span>Reset/New Task</span>
            </button>
            {taskStatus === "completed" && finalResult && (
              <button 
                onClick={downloadResult}
                className="px-3.5 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-[11px] text-white font-semibold flex items-center gap-1.5 shadow glow-primary/20 transition cursor-pointer"
              >
                <FileDown className="w-3.5 h-3.5" />
                <span>Export Report</span>
              </button>
            )}
            <button 
              onClick={handleDelete}
              disabled={isDeleting}
              className="px-3 py-1.5 rounded bg-rose-950/40 hover:bg-rose-900/60 border border-rose-900/50 text-[11px] text-rose-300 font-semibold flex items-center gap-1.5 transition disabled:opacity-50 cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>{isDeleting ? "Deleting..." : "Delete Task"}</span>
            </button>
          </div>
        )}
      </div>

      {/* Main Workspace Workspace Panes */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden h-[calc(100vh-84px)]">
        
        {/* Left Side Column: Form input or active Tasks list (span 4) */}
        <div className="lg:col-span-4 border-r border-slate-900 p-6 overflow-y-auto flex flex-col gap-6 bg-slate-950/20">
          {!taskId ? (
            <div className="glass-panel border border-slate-800 rounded-xl p-5 space-y-5 premium-glow-blue relative overflow-hidden">
              <div className="absolute top-0 right-0 w-16 h-16 bg-blue-600/5 rounded-full blur-xl pointer-events-none" />
              
              <div className="flex items-center gap-2 border-b border-slate-900 pb-3">
                <Sparkles className="w-4 h-4 text-blue-450 animate-pulse" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Deploy Workforce Flow
                </h3>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">
                    1. Select Target Plugin Workflow
                  </label>
                  <select 
                    value={selectedPlugin}
                    onChange={(e) => setSelectedPlugin(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800/80 rounded-lg px-3.5 py-2.5 text-xs text-slate-300 font-medium focus:outline-none focus:border-blue-500/60 transition-all"
                  >
                    {plugins.map((p) => (
                      <option key={p.plugin_id} value={p.plugin_id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                  <p className="text-[10px] text-slate-650 leading-normal font-medium">
                    {plugins.find(p => p.plugin_id === selectedPlugin)?.description}
                  </p>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">
                    2. Describe Goal Objectives
                  </label>
                  <textarea 
                    rows={6}
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Provide detailed goals for the workforce. E.g. 'Build a python script implementing a token bucketer' or 'Perform startup analysis on AI voice agents markets.'"
                    className="w-full bg-slate-950 border border-slate-800/80 rounded-lg p-3.5 text-xs text-slate-300 focus:outline-none focus:border-blue-500/60 transition-all leading-relaxed resize-none"
                  />
                </div>

                <button 
                  type="submit"
                  disabled={!prompt.trim() || isSubmitting}
                  className="w-full py-3 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-650 hover:from-blue-500 hover:to-indigo-550 text-xs font-bold text-white flex items-center justify-center gap-2 transition duration-300 glow-primary disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Planning workforce steps...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3 h-3 fill-white" />
                      <span>Orchestrate Workforce Flow</span>
                    </>
                  )}
                </button>
              </form>
            </div>
          ) : (
            <div className="space-y-5 flex flex-col h-full overflow-hidden">
              <div className="glass-panel border border-slate-805 rounded-xl p-4 space-y-2 premium-glow-purple relative overflow-hidden">
                <div className="absolute top-0 right-0 w-16 h-16 bg-purple-650/5 rounded-full blur-xl pointer-events-none" />
                <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block">Goal Objective:</span>
                <p className="text-xs text-slate-300 leading-relaxed line-clamp-4 font-medium">{prompt}</p>
                
                {/* Confidence bar if verified */}
                {confidenceScore !== null && (
                  <div className="pt-2 border-t border-slate-900 mt-2 flex items-center justify-between text-[10px]">
                    <span className="text-slate-500 font-medium">Fact Verification Certainty:</span>
                    <span className="font-bold text-emerald-400">{Math.round(confidenceScore * 100)}%</span>
                  </div>
                )}
              </div>
              
              <div className="flex-1 overflow-y-auto">
                <Timeline subtasks={subtasks} />
              </div>
            </div>
          )}
        </div>

        {/* Right Side Column: Tab Viewports (span 8) */}
        <div className="lg:col-span-8 p-6 overflow-y-auto flex flex-col h-full gap-5 bg-slate-950/10">
          {/* Tabs header selector */}
          <div className="flex items-center gap-1.5 border-b border-slate-900 pb-2">
            {[
              { id: "graph", label: "Workflow Graph", icon: BrainCircuit },
              { id: "timeline", label: "Timeline Progress", icon: ListTodo },
              { id: "terminal", label: "Thinking Console", icon: TermIcon },
              { id: "result", label: "Verified Output", icon: CheckCircle, disabled: !finalResult }
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  disabled={tab.disabled}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-bold tracking-wide border transition-all duration-300 cursor-pointer ${
                    isActive 
                      ? "bg-blue-600/10 border-blue-500/40 text-blue-450 glow-primary/5 scale-[1.03]" 
                      : tab.disabled 
                      ? "border-transparent text-slate-805 cursor-not-allowed opacity-40" 
                      : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40 hover:scale-[1.01]"
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? "text-blue-400 animate-pulse" : ""}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Tab Content Display */}
          <div className="flex-1 min-h-0 overflow-y-auto">
            {activeTab === "graph" && (
              <div className="h-full">
                <WorkflowGraph subtasks={subtasks} taskStatus={taskStatus} />
              </div>
            )}
            
            {activeTab === "timeline" && (
              <div className="h-full">
                <Timeline subtasks={subtasks} />
              </div>
            )}

            {activeTab === "terminal" && (
              <div className="h-full">
                <AgentTerminal logs={logs} isStreaming={isStreaming} />
              </div>
            )}

            {activeTab === "result" && finalResult && (
              <div className="glass-panel border border-slate-800 rounded-xl p-7 text-slate-100 overflow-y-auto leading-relaxed shadow-xl max-w-4xl mx-auto select-text">
                <MarkdownRenderer content={finalResult} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Workspace() {
  return (
    <Suspense fallback={
      <div className="flex-1 flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
          <p className="text-xs text-slate-500 font-medium">Loading workspace...</p>
        </div>
      </div>
    }>
      <WorkspaceInner />
    </Suspense>
  );
}
