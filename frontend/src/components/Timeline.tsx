"use client";

import { useState } from "react";
import { CheckCircle2, Clock, Loader2, AlertCircle, ChevronDown, ChevronUp } from "lucide-react";

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

interface TimelineProps {
  subtasks: Subtask[];
}

export default function Timeline({ subtasks }: TimelineProps) {
  const [expandedSubtask, setExpandedSubtask] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    if (expandedSubtask === id) {
      setExpandedSubtask(null);
    } else {
      setExpandedSubtask(id);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />;
      case "running":
        return <Loader2 className="w-5 h-5 text-[#da7756] animate-spin shrink-0" />;
      case "failed":
        return <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />;
      default:
        return <Clock className="w-5 h-5 text-zinc-600 shrink-0" />;
    }
  };

  const getAgentLabel = (agent: string) => {
    switch (agent) {
      case "researcher": return "Research Agent";
      case "reasoner": return "Reasoning Agent";
      case "analyst": return "Analyst Agent";
      case "executor": return "Execution Agent";
      case "memory_agent": return "Memory Agent";
      case "verifier": return "Verifier Agent";
      default: return "Planner Agent";
    }
  };

  if (subtasks.length === 0) {
    return (
      <div className="text-zinc-500 text-xs italic text-center p-8 bg-[#141416] border border-zinc-800 rounded-2xl">
        Waiting for Planner Agent to partition subtasks...
      </div>
    );
  }

  return (
    <div className="space-y-3 pr-1">
      {subtasks.map((sub, idx) => {
        const isExpanded = expandedSubtask === sub.id;
        const isRunning = sub.status === "running";
        const isCompleted = sub.status === "completed";
        
        return (
          <div 
            key={sub.id} 
            className={`rounded-2xl transition-all duration-200 border ${
              isRunning 
                ? "border-[#da7756]/50 bg-[#da7756]/10" 
                : isCompleted 
                ? "border-zinc-800 bg-[#18181b] hover:border-zinc-700" 
                : "border-zinc-800/60 bg-[#141416] opacity-60"
            }`}
          >
            {/* Card Header Row */}
            <div 
              onClick={() => isCompleted && toggleExpand(sub.id)}
              className={`p-4 flex items-center justify-between gap-3 select-none ${
                isCompleted ? "cursor-pointer" : ""
              }`}
            >
              <div className="flex items-center gap-3">
                {getStatusIcon(sub.status)}
                <div>
                  <h5 className={`text-xs font-bold ${isRunning ? "text-[#da7756]" : isCompleted ? "text-white" : "text-zinc-400"}`}>
                    Step {idx + 1}: {sub.title}
                  </h5>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] uppercase tracking-wider font-semibold text-zinc-400">
                      {getAgentLabel(sub.assigned_agent)}
                    </span>
                    {sub.confidence_score > 0 && (
                      <span className="text-[9px] bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 px-1.5 py-0.2 rounded-full font-bold">
                        Conf: {Math.round(sub.confidence_score * 100)}%
                      </span>
                    )}
                  </div>
                </div>
              </div>
              
              {isCompleted && (
                <div className="text-zinc-400 p-1 hover:text-white transition">
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </div>
              )}
            </div>

            {/* Expansion Content */}
            {(isExpanded || isRunning) && (
              <div className="px-4 pb-4 border-t border-zinc-800 pt-3 text-xs space-y-3">
                <div className="text-zinc-300 font-medium leading-relaxed">
                  <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider block mb-1">
                    Execution Directive:
                  </span>
                  <p className="bg-[#121214] p-3 rounded-xl border border-zinc-800 text-zinc-300 text-xs leading-relaxed">
                    {sub.description}
                  </p>
                </div>
                
                {isCompleted && sub.output && (
                  <div className="bg-[#121214] border border-zinc-800 p-3.5 rounded-xl font-mono text-[11px] text-zinc-300 max-h-56 overflow-y-auto whitespace-pre-wrap select-text leading-relaxed">
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-1.5 mb-2.5">
                      <span className="text-[9px] font-bold text-[#da7756] uppercase tracking-widest">
                        Agent Generated Output
                      </span>
                      <span className="text-[9px] text-zinc-500 font-mono">step_{idx + 1}.log</span>
                    </div>
                    {sub.output}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
