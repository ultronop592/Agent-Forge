"use client";

import { useState, useEffect } from "react";
import { 
  CheckCircle, 
  XCircle, 
  Plus, 
  Trash2, 
  ArrowUp, 
  ArrowDown, 
  Layers,
  Clock,
  Sparkles
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
  { value: "memory_agent", label: "Memory (Vector Librarian)" },
  { value: "analyst", label: "Analyst (Live Web Search & Reasoning)" },
  { value: "executor", label: "Executor (Code & Report Builder)" },
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
  const [secondsLeft, setSecondsLeft] = useState(60);

  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleTitleChange = (index: number, newTitle: string) => {
    setSubtasks((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], title: newTitle };
      return copy;
    });
  };

  const handleDescriptionChange = (index: number, newDesc: string) => {
    setSubtasks((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], description: newDesc };
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

  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    setSubtasks((prev) => {
      const copy = [...prev];
      const temp = copy[index - 1];
      copy[index - 1] = copy[index];
      copy[index] = temp;
      return copy;
    });
  };

  const handleMoveDown = (index: number) => {
    if (index === subtasks.length - 1) return;
    setSubtasks((prev) => {
      const copy = [...prev];
      const temp = copy[index + 1];
      copy[index + 1] = copy[index];
      copy[index] = temp;
      return copy;
    });
  };

  const handleRemoveSubtask = (index: number) => {
    if (subtasks.length <= 1) return;
    setSubtasks((prev) => prev.filter((_, i) => i !== index));
  };

  const handleAddSubtask = () => {
    setSubtasks((prev) => [
      ...prev,
      {
        title: `Custom Subtask Step ${prev.length + 1}`,
        description: "Specify execution instructions...",
        assigned_agent: "executor",
      },
    ]);
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
    <div className="glass-panel-elevated rounded-2xl p-6 space-y-5 border border-sky-500/30 shadow-2xl relative overflow-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-sky-500/20 text-sky-400 flex items-center justify-center">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>Human-in-the-Loop: Plan Review & Edit Gate</span>
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            </h3>
            <p className="text-xs text-slate-400">
              Review, re-order, modify agent assignments, or add custom subtask steps before execution begins.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-xl shrink-0">
          <Clock className="w-3.5 h-3.5 text-amber-400 animate-spin" />
          <span className="text-[11px] font-semibold text-slate-300">
            Auto-proceeds in: <strong className="text-amber-400 font-mono">{secondsLeft}s</strong>
          </span>
        </div>
      </div>

      {/* Subtasks List */}
      <div className="space-y-3 max-h-[50vh] overflow-y-auto pr-1">
        {subtasks.map((subtask, index) => (
          <div
            key={subtask.id || `subtask-${index}`}
            className="p-4 rounded-xl bg-[#080b12] border border-slate-800/90 hover:border-slate-700 transition space-y-3"
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-[10px] font-bold text-sky-400 bg-sky-500/10 border border-sky-500/20 px-2 py-0.5 rounded-md uppercase">
                Step {index + 1}
              </span>

              <select
                value={subtask.assigned_agent}
                onChange={(e) => handleAgentChange(index, e.target.value)}
                className="bg-[#05070c] border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200 font-medium focus:outline-none focus:border-sky-500/50"
              >
                {AGENT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <input
              type="text"
              value={subtask.title}
              onChange={(e) => handleTitleChange(index, e.target.value)}
              placeholder="Step Title..."
              className="w-full bg-[#05070c] border border-slate-800 rounded-lg px-3 py-2 text-xs font-semibold text-white focus:outline-none focus:border-sky-500/60"
            />

            <textarea
              rows={2}
              value={subtask.description}
              onChange={(e) => handleDescriptionChange(index, e.target.value)}
              placeholder="Execution description & instructions..."
              className="w-full bg-[#05070c] border border-slate-800 rounded-lg p-2.5 text-xs text-slate-300 focus:outline-none focus:border-sky-500/60 resize-none"
            />

            <div className="flex items-center justify-end gap-1.5 pt-1">
              <button
                type="button"
                onClick={() => handleMoveUp(index)}
                disabled={index === 0}
                className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white disabled:opacity-30 cursor-pointer"
                title="Move up"
              >
                <ArrowUp className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => handleMoveDown(index)}
                disabled={index === subtasks.length - 1}
                className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white disabled:opacity-30 cursor-pointer"
                title="Move down"
              >
                <ArrowDown className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => handleRemoveSubtask(index)}
                disabled={subtasks.length <= 1}
                className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 disabled:opacity-30 cursor-pointer"
                title="Delete step"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Primary Actions Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-slate-800">
        <button
          type="button"
          onClick={handleAddSubtask}
          className="flex items-center gap-2 text-xs font-semibold text-sky-400 hover:text-sky-300 bg-sky-500/10 border border-sky-500/20 hover:border-sky-500/40 rounded-xl px-4 py-2.5 transition w-full sm:w-auto justify-center cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Add Custom Step</span>
        </button>

        <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
          <button
            type="button"
            onClick={handleRejectClick}
            disabled={isSubmitting}
            className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer"
          >
            <XCircle className="w-4 h-4 text-rose-400" />
            <span>Cancel Task</span>
          </button>
          <button
            type="button"
            onClick={handleApproveClick}
            disabled={isSubmitting}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white text-xs font-bold shadow-lg shadow-sky-950/50 flex items-center gap-2 transition glow-primary cursor-pointer"
          >
            <CheckCircle className="w-4 h-4" />
            <span>Approve & Run Plan</span>
          </button>
        </div>
      </div>
    </div>
  );
}
