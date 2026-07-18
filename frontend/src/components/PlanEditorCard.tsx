"use client";

import { useState } from "react";
import { 
  CheckCircle, 
  XCircle, 
  Plus, 
  Trash2, 
  ArrowUp, 
  ArrowDown, 
  Layers
} from "lucide-react";

export interface EditableSubtask {
  id?: string;
  title: string;
  description: string;
  assigned_agent: string;
}

interface PlanEditorCardProps {
  initialSubtasks: EditableSubtask[];
  onApprove: (subtasks: EditableSubtask[]) => Promise<void>;
  onReject: () => Promise<void>;
}

const AGENT_OPTIONS = [
  { value: "memory_agent", label: "Memory (Institutional Librarian)" },
  { value: "analyst", label: "Analyst (Web Search & Reasoning)" },
  { value: "executor", label: "Executor (Deliverable Builder)" },
  { value: "verifier", label: "Verifier (QA Fact-Checker)" },
];

export default function PlanEditorCard({ initialSubtasks, onApprove, onReject }: PlanEditorCardProps) {
  const [subtasks, setSubtasks] = useState<EditableSubtask[]>(
    initialSubtasks.length > 0
      ? initialSubtasks
      : [
          { title: "Search past memory for contextual insights", description: "", assigned_agent: "memory_agent" },
          { title: "Conduct web research & SWOT analysis", description: "", assigned_agent: "analyst" },
          { title: "Synthesize findings & build deliverable", description: "", assigned_agent: "executor" },
          { title: "Verify quality and compliance", description: "", assigned_agent: "verifier" },
        ]
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleTitleChange = (index: number, newTitle: string) => {
    setSubtasks((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], title: newTitle };
      return copy;
    });
  };

  const handleAgentChange = (index: number, newAgent: string) => {
    setSubtasks((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], assigned_agent: newAgent };
      return copy;
    });
  };

  const handleAddSubtask = () => {
    setSubtasks((prev) => [
      ...prev,
      {
        title: "New Subtask step...",
        description: "",
        assigned_agent: "analyst",
      },
    ]);
  };

  const handleDeleteSubtask = (index: number) => {
    if (subtasks.length <= 1) return;
    setSubtasks((prev) => prev.filter((_, i) => i !== index));
  };

  const handleMove = (index: number, direction: "up" | "down") => {
    const targetIdx = direction === "up" ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= subtasks.length) return;
    setSubtasks((prev) => {
      const copy = [...prev];
      const temp = copy[index];
      copy[index] = copy[targetIdx];
      copy[targetIdx] = temp;
      return copy;
    });
  };

  const handleApproveClick = async () => {
    setIsSubmitting(true);
    try {
      await onApprove(subtasks);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRejectClick = async () => {
    setIsSubmitting(true);
    try {
      await onReject();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="glass-panel border-2 border-amber-500/40 rounded-2xl p-6 shadow-2xl relative overflow-hidden bg-slate-950/80 mb-8 animate-fade-in">
      <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-850 pb-4 mb-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <Layers className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="bg-amber-500/20 text-amber-400 border border-amber-500/40 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider">
                Human-in-the-Loop Gate
              </span>
              <span className="text-xs text-slate-400 font-semibold">Plan Generated</span>
            </div>
            <h3 className="text-lg font-bold text-white mt-1">Review & Customize Execution Plan</h3>
          </div>
        </div>
        <p className="text-xs text-slate-400 max-w-sm font-medium">
          Edit subtask sequence, adjust agent assignments, or add steps before launching execution.
        </p>
      </div>

      {/* Subtasks List Editor */}
      <div className="space-y-3 mb-6 max-h-96 overflow-y-auto pr-1">
        {subtasks.map((sub, index) => (
          <div 
            key={index}
            className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 hover:border-slate-750 transition-all"
          >
            {/* Step Number Badge */}
            <div className="flex items-center gap-2 min-w-[28px]">
              <span className="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 font-bold text-xs flex items-center justify-center">
                {index + 1}
              </span>
            </div>

            {/* Editable Title Input */}
            <input 
              type="text"
              value={sub.title}
              onChange={(e) => handleTitleChange(index, e.target.value)}
              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-medium focus:outline-none focus:border-amber-500/50 transition-colors"
              placeholder="Subtask title..."
            />

            {/* Agent Selector Dropdown */}
            <select
              value={sub.assigned_agent}
              onChange={(e) => handleAgentChange(index, e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-amber-300 font-medium focus:outline-none focus:border-amber-500/50 min-w-[200px]"
            >
              {AGENT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            {/* Ordering & Delete Controls */}
            <div className="flex items-center gap-1.5 justify-end">
              <button
                type="button"
                onClick={() => handleMove(index, "up")}
                disabled={index === 0}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:pointer-events-none transition-colors"
                title="Move up"
              >
                <ArrowUp className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => handleMove(index, "down")}
                disabled={index === subtasks.length - 1}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:pointer-events-none transition-colors"
                title="Move down"
              >
                <ArrowDown className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => handleDeleteSubtask(index)}
                disabled={subtasks.length <= 1}
                className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 disabled:opacity-30 disabled:pointer-events-none transition-colors"
                title="Delete step"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Add Step & Primary Actions Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-3 border-t border-slate-850">
        <button
          type="button"
          onClick={handleAddSubtask}
          className="flex items-center gap-2 text-xs font-semibold text-amber-400 hover:text-amber-300 bg-amber-500/10 border border-amber-500/20 hover:border-amber-500/40 rounded-xl px-4 py-2.5 transition-all w-full sm:w-auto justify-center"
        >
          <Plus className="w-4 h-4" />
          <span>Add Custom Subtask Step</span>
        </button>

        <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
          <button
            type="button"
            onClick={handleRejectClick}
            disabled={isSubmitting}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs font-bold transition-all disabled:opacity-50"
          >
            <XCircle className="w-4 h-4" />
            <span>Reject Task</span>
          </button>

          <button
            type="button"
            onClick={handleApproveClick}
            disabled={isSubmitting}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white text-xs font-extrabold shadow-lg shadow-emerald-900/30 transition-all hover:scale-[1.02] disabled:opacity-50"
          >
            <CheckCircle className="w-4 h-4" />
            <span>Approve Plan & Launch Execution</span>
          </button>
        </div>
      </div>
    </div>
  );
}
