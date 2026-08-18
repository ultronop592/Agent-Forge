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
  Trash2,
  Copy,
  Check,
  Zap,
  Activity,
  ShieldCheck
} from "lucide-react";
import PlanEditorCard, { EditableSubtask } from "@/components/PlanEditorCard";
import SteeringPanel from "@/components/SteeringPanel";
import DeleteConfirmModal from "@/components/DeleteConfirmModal";

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
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [copied, setCopied] = useState(false);

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
      const data = await api.getTask(id);
      setTaskId(data.id);
      setPrompt(data.prompt);
      setTaskStatus(data.status);
      setSubtasks(data.subtasks || []);
      setLogs(data.logs || []);
      setFinalResult(data.final_result || "");
      setConfidenceScore(data.confidence_score);

      if (data.status === "completed" && data.final_result) {
        setActiveTab("result");
      } else if (data.status === "running" || data.status === "awaiting_plan_approval" || data.status === "awaiting_steering") {
        connectSSE(data.id);
      }
    } catch (e) {
      console.error("Failed to load task:", e);
    }
  };

  const connectSSE = (tId: string) => {
    disconnectStream();
    setIsStreaming(true);

    const sse = new EventSource(api.getStreamUrl(tId));
    eventSourceRef.current = sse;

    sse.onmessage = (event: MessageEvent) => {
      reconnectAttemptsRef.current = 0;
      try {
        const payload = JSON.parse(event.data);
        handleStreamPayload(payload);
      } catch (e) {
        console.error("Malformed SSE payload", e);
      }
    };

    sse.onerror = () => {
      console.warn("SSE stream disconnected.");
      disconnectStream();

      if (reconnectAttemptsRef.current < 5) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
        reconnectAttemptsRef.current += 1;
        reconnectTimerRef.current = setTimeout(() => {
          connectSSE(tId);
        }, delay);
      } else {
        setIsStreaming(false);
      }
    };
  };

  const disconnectStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsStreaming(false);
  };

  const handleStreamPayload = (payload: any) => {
    const { event_type, data } = payload;

    if (event_type === "task_status") {
      setTaskStatus(data.status);
      if (data.status === "completed") {
        setIsStreaming(false);
        disconnectStream();
        if (data.final_result) {
          setFinalResult(data.final_result);
          setActiveTab("result");
        }
      }
      if (data.confidence_score) {
        setConfidenceScore(data.confidence_score);
      }
    } else if (event_type === "subtasks_update") {
      setSubtasks(data.subtasks);
    } else if (event_type === "agent_log") {
      setLogs((prev) => [...prev, data]);
    } else if (event_type === "final_result") {
      setFinalResult(data.final_result);
      setTaskStatus("completed");
      setActiveTab("result");
      disconnectStream();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isSubmitting || !selectedPlugin) return;

    setIsSubmitting(true);
    resetWorkspace();

    try {
      const task = await api.createTask(prompt, selectedPlugin);
      setTaskId(task.id);
      setTaskStatus("running");
      router.push(`/chat?task_id=${task.id}`);
      connectSSE(task.id);
    } catch (err) {
      console.error("Workspace launch failed:", err);
      setTaskStatus("failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleApprovePlan = async (modifiedSubtasks?: EditableSubtask[]) => {
    if (!taskId) return;
    try {
      await api.approvePlan(taskId, modifiedSubtasks);
      setTaskStatus("running");
    } catch (e: any) {
      console.error("Failed to approve plan:", e);
    }
  };

  const handleSteerTask = async (instructions: string) => {
    if (!taskId) return;
    try {
      await api.steerTask(taskId, instructions, "steer");
      setTaskStatus("running");
    } catch (e: any) {
      console.error("Failed to steer task:", e);
    }
  };

  const handleForceCompleteTask = async () => {
    if (!taskId) return;
    try {
      await api.steerTask(taskId, "", "force_complete");
      setTaskStatus("completed");
      setActiveTab("result");
    } catch (e: any) {
      console.error("Failed to force complete:", e);
    }
  };

  const handleRejectTask = async () => {
    if (!taskId) return;
    try {
      await api.rejectTask(taskId, "Cancelled by user");
      setTaskStatus("cancelled");
      disconnectStream();
    } catch (e: any) {
      console.error("Failed to cancel task:", e);
    }
  };

  const downloadResult = () => {
    if (!finalResult) return;
    const blob = new Blob([finalResult], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `agentforge_report_${taskId}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const copyResultToClipboard = () => {
    if (!finalResult) return;
    navigator.clipboard.writeText(finalResult);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleOpenDeleteModal = () => {
    setDeleteError(null);
    setShowDeleteModal(true);
  };

  const handleConfirmDelete = async () => {
    if (!taskId) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteTask(taskId);
      setShowDeleteModal(false);
      router.push("/chat");
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full min-h-screen relative z-10 select-none">
      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={showDeleteModal}
        onClose={() => {
          if (!isDeleting) {
            setShowDeleteModal(false);
            setDeleteError(null);
          }
        }}
        onConfirm={handleConfirmDelete}
        title="Delete Workforce Task"
        description="Are you sure you want to permanently delete this task workspace? All agent subtasks, execution logs, and verified reports will be erased."
        itemLabel={prompt || `Task ID: ${taskId}`}
        itemSubLabel={taskId ? `ID: ${taskId}` : undefined}
        confirmText="Delete Task"
        isLoading={isDeleting}
        errorMessage={deleteError}
      />

      {/* Upper Navigation Header */}
      <div className="border-b border-slate-800/80 bg-[#090d16]/95 backdrop-blur-xl px-7 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-sky-500/15 border border-sky-500/30 text-sky-400 flex items-center justify-center shadow-sm">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white tracking-tight">
                  AI Workforce Workspace
                </h2>
                {taskId && (
                  <span className={`px-2 py-0.5 rounded-full border text-[9px] font-bold uppercase tracking-wider ${
                    taskStatus === "completed"
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      : taskStatus === "running"
                      ? "bg-sky-500/10 text-sky-400 border-sky-500/20 animate-pulse"
                      : taskStatus === "awaiting_plan_approval" || taskStatus === "awaiting_steering"
                      ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                      : "bg-slate-900 text-slate-400 border-slate-800"
                  }`}>
                    {taskStatus}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 font-medium">
                Autonomous subtask division, real-time thinking logs, and verified deliverable outputs.
              </p>
            </div>
          </div>
        </div>

        {taskId && (
          <div className="flex items-center gap-2.5">
            <button 
              onClick={() => router.push("/chat")}
              className="px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-xs font-semibold text-slate-300 hover:text-white border border-slate-800 flex items-center gap-1.5 transition cursor-pointer"
            >
              <RefreshCcw className="w-3.5 h-3.5" />
              <span>New Task</span>
            </button>

            {taskStatus === "completed" && finalResult && (
              <button 
                onClick={downloadResult}
                className="px-4 py-1.5 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-xs font-bold text-white flex items-center gap-1.5 shadow-lg shadow-sky-950/40 glow-primary transition cursor-pointer"
              >
                <FileDown className="w-3.5 h-3.5" />
                <span>Export Report</span>
              </button>
            )}

            <button 
              onClick={handleOpenDeleteModal}
              className="px-3.5 py-1.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-xs font-semibold text-rose-400 flex items-center gap-1.5 transition cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Delete Task</span>
            </button>
          </div>
        )}
      </div>

      {/* Main Workspace Workspace Panes */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden h-[calc(100vh-73px)]">
        
        {/* Left Side Column: Form input or active Tasks list (span 4) */}
        <div className="lg:col-span-4 border-r border-slate-800/80 p-6 overflow-y-auto flex flex-col gap-5 bg-[#080b12]">
          {!taskId ? (
            <div className="glass-panel-elevated rounded-2xl p-6 space-y-5 relative overflow-hidden">
              <div className="flex items-center gap-2.5 border-b border-slate-800 pb-3.5">
                <div className="w-7 h-7 rounded-lg bg-sky-500/20 text-sky-400 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 animate-pulse" />
                </div>
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-white">
                    Deploy Workforce Flow
                  </h3>
                  <span className="text-[10px] text-slate-500">Configure parameters & target goal</span>
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                    1. Target Plugin Workflow
                  </label>
                  <select 
                    value={selectedPlugin}
                    onChange={(e) => setSelectedPlugin(e.target.value)}
                    className="w-full bg-[#080b12] border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 font-medium focus:outline-none focus:border-sky-500/60 transition cursor-pointer"
                  >
                    {plugins.map((p) => (
                      <option key={p.plugin_id} value={p.plugin_id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                  <p className="text-[10px] text-slate-500 leading-normal font-medium pt-0.5">
                    {plugins.find(p => p.plugin_id === selectedPlugin)?.description}
                  </p>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                    2. Objective Description
                  </label>
                  <textarea 
                    rows={6}
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Provide specific objectives for the workforce. E.g. 'Search and aggregate today's AI developer jobs in India' or 'Build a Python token bucket rate limiter'..."
                    className="w-full bg-[#080b12] border border-slate-800 rounded-xl p-3.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500/60 transition leading-relaxed resize-none"
                  />
                </div>

                <button 
                  type="submit"
                  disabled={!prompt.trim() || isSubmitting}
                  className="w-full py-3 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-xs font-bold text-white flex items-center justify-center gap-2 transition duration-300 glow-primary disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
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
            <div className="space-y-4 flex flex-col h-full overflow-hidden">
              {/* Goal summary header */}
              <div className="glass-panel rounded-2xl p-4 space-y-2.5 border border-slate-800/80">
                <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block">
                  Goal Objective:
                </span>
                <p className="text-xs text-slate-200 leading-relaxed font-medium select-text">{prompt}</p>
                
                {/* Confidence bar if verified */}
                {confidenceScore !== null && (
                  <div className="pt-2.5 border-t border-slate-800/80 mt-2 flex items-center justify-between text-[10px]">
                    <span className="text-slate-400 font-medium flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      <span>QA Verification Rating:</span>
                    </span>
                    <span className="font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                      {Math.round(confidenceScore * 100)}%
                    </span>
                  </div>
                )}
              </div>
              
              {/* Subtask Timeline partition */}
              <div className="flex-1 overflow-y-auto">
                <div className="px-1 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  Subtask Partition Execution Timeline
                </div>
                <Timeline subtasks={subtasks} />
              </div>
            </div>
          )}
        </div>

        {/* Right Side Column: Tab Viewports (span 8) */}
        <div className="lg:col-span-8 p-6 overflow-y-auto flex flex-col h-full gap-5 bg-[#07090e]">
          {/* HITL Plan Approval Gate */}
          {taskStatus === "awaiting_plan_approval" && (
            <PlanEditorCard
              initialSubtasks={subtasks}
              onApprove={handleApprovePlan}
              onReject={handleRejectTask}
            />
          )}

          {/* HITL Dynamic Steering Intercept Panel */}
          {taskStatus === "awaiting_steering" && (
            <SteeringPanel
              confidenceScore={confidenceScore}
              verifierFeedback={
                logs.filter((l) => l.agent_name === "Verifier").pop()?.content ||
                "The Verifier requested feedback on the deliverable prior to final verification."
              }
              onSteer={handleSteerTask}
              onForceComplete={handleForceCompleteTask}
              onCancel={handleRejectTask}
            />
          )}

          {/* Tabs header selector */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
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
                    className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold tracking-wide transition-all duration-200 cursor-pointer ${
                      isActive 
                        ? "bg-sky-500/15 border border-sky-500/40 text-white shadow-sm shadow-sky-500/10" 
                        : tab.disabled 
                        ? "border border-transparent text-slate-600 cursor-not-allowed opacity-40" 
                        : "border border-transparent text-slate-400 hover:text-white hover:bg-slate-900/60"
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isActive ? "text-sky-400" : ""}`} />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {activeTab === "result" && finalResult && (
              <div className="flex items-center gap-2">
                <button
                  onClick={copyResultToClipboard}
                  className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-emerald-400">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy Markdown</span>
                    </>
                  )}
                </button>
              </div>
            )}
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
              <div className="glass-panel-elevated rounded-2xl p-7 text-slate-100 overflow-y-auto leading-relaxed shadow-2xl max-w-4xl mx-auto select-text border border-slate-800">
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
      <div className="flex-1 flex items-center justify-center min-h-screen bg-[#07090e]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-sky-500/30 border-t-sky-400 rounded-full animate-spin" />
          <p className="text-xs text-slate-400 font-semibold tracking-wider uppercase">Loading workspace...</p>
        </div>
      </div>
    }>
      <WorkspaceInner />
    </Suspense>
  );
}
