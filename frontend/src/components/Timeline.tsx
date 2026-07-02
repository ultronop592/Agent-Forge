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
        return <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />;
      case "running":
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin shrink-0" />;
      case "failed":
        return <AlertCircle className="w-5 h-5 text-rose-500 shrink-0" />;
      default:
        return <Clock className="w-5 h-5 text-slate-700 shrink-0" />;
    }
  };

  const getAgentLabel = (agent: string) => {
    switch (agent) {
      case "researcher": return "Research Agent";
      case "reasoner": return "Reasoning Agent";
      case "executor": return "Execution Agent";
      case "memory_agent": return "Memory Agent";
      case "verifier": return "Verifier Agent";
      default: return "Planner Agent";
    }
  };

  if (subtasks.length === 0) {
    return (
      <div className="text-slate-500 text-xs italic text-center p-6 bg-slate-950 border border-slate-900 rounded-xl">
        Waiting for Planner Agent to partition subtasks...
      </div>
    );
  }

  return (
    <div className="glass-panel border border-slate-800 rounded-xl p-5 flex flex-col h-full overflow-hidden shadow-xl">
      <h4 className="text-xs text-slate-300 font-semibold uppercase tracking-wider mb-4 border-b border-slate-900 pb-3">
        Subtask Partition Execution Timeline
      </h4>
      
      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {subtasks.map((sub, idx) => {
          const isExpanded = expandedSubtask === sub.id;
          const isRunning = sub.status === "running";
          const isCompleted = sub.status === "completed";
          
          return (
            <div 
              key={sub.id} 
              className={`border rounded-lg transition-all duration-200 ${
                isRunning 
                  ? "border-blue-500/40 bg-blue-950/5" 
                  : isCompleted 
                  ? "border-slate-800/80 bg-slate-950/20" 
                  : "border-slate-900/60 bg-slate-950/50"
              }`}
            >
              {/* Card Header Row */}
              <div 
                onClick={() => isCompleted && toggleExpand(sub.id)}
                className={`p-4 flex items-center justify-between gap-4 select-none ${
                  isCompleted ? "cursor-pointer hover:bg-slate-900/10" : ""
                }`}
              >
                <div className="flex items-center gap-3.5">
                  {getStatusIcon(sub.status)}
                  <div>
                    <h5 className={`text-xs font-semibold ${isRunning ? "text-blue-400" : isCompleted ? "text-slate-100" : "text-slate-500"}`}>
                      Step {idx + 1}: {sub.title}
                    </h5>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[9px] uppercase tracking-wider font-bold text-slate-500">
                        {getAgentLabel(sub.assigned_agent)}
                      </span>
                      {sub.confidence_score > 0 && (
                        <span className="text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1 py-0.2 rounded font-semibold">
                          Conf: {Math.round(sub.confidence_score * 100)}%
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                
                {isCompleted && (
                  <div>
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-slate-500" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-slate-500" />
                    )}
                  </div>
                )}
              </div>

              {/* Expansion content */}
              {(isExpanded || isRunning) && (
                <div className="px-4 pb-4 border-t border-slate-900/60 pt-3 text-xs">
                  <div className="text-slate-400 font-medium leading-relaxed mb-3">
                    <span className="text-slate-500 font-semibold block mb-0.5 uppercase text-[9px] tracking-wide">Directive:</span>
                    {sub.description}
                  </div>
                  
                  {isCompleted && sub.output && (
                    <div className="bg-slate-950 border border-slate-900/80 p-3.5 rounded font-mono text-[10px] text-slate-400 max-h-48 overflow-y-auto whitespace-pre-wrap select-text leading-relaxed">
                      <span className="text-[9px] font-bold text-slate-500 uppercase block border-b border-slate-900 pb-1 mb-2 tracking-widest">
                        Agent Outputs
                      </span>
                      {sub.output}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
