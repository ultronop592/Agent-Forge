"use client";

import { 
  Compass, 
  Search, 
  BrainCircuit, 
  FileCode, 
  ShieldCheck, 
  FolderGit,
  Layers
} from "lucide-react";

interface AgentCardProps {
  name: string;
  role: string;
  status: "idle" | "thinking" | "tool_call" | "completed" | "failed";
  description: string;
  tools: string[];
}

const AGENT_ICONS: Record<string, any> = {
  "Planner": Compass,
  "Manager": Layers,
  "Analyst": Search,
  "Researcher": Search,
  "Reasoner": BrainCircuit,
  "Executor": FileCode,
  "Verifier": ShieldCheck,
  "MemoryAgent": FolderGit
};

const STATUS_COLORS: Record<string, string> = {
  idle: "bg-slate-500/20 text-slate-400 border-slate-500/30",
  thinking: "bg-blue-500/20 text-blue-400 border-blue-500/40 pulse-active",
  tool_call: "bg-amber-500/20 text-amber-400 border-amber-500/40",
  completed: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  failed: "bg-rose-500/20 text-rose-400 border-rose-500/30"
};

export default function AgentCard({ name, role, status, description, tools }: AgentCardProps) {
  const Icon = AGENT_ICONS[name] || BrainCircuit;
  const statusColor = STATUS_COLORS[status] || STATUS_COLORS.idle;

  return (
    <div className="glass-panel hover:bg-slate-900/30 transition-all duration-300 rounded-xl p-5 border border-slate-800 flex flex-col justify-between h-48 relative overflow-hidden group">
      {/* Background glow when active */}
      {status === "thinking" && (
        <div className="absolute -top-12 -right-12 w-24 h-24 bg-blue-500/10 rounded-full blur-xl pointer-events-none" />
      )}
      {status === "completed" && (
        <div className="absolute -top-12 -right-12 w-24 h-24 bg-emerald-500/5 rounded-full blur-xl pointer-events-none" />
      )}

      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-3.5">
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center border transition-all ${
              status === "thinking"
                ? "bg-blue-600/10 border-blue-500/40 text-blue-400"
                : status === "completed"
                ? "bg-emerald-600/10 border-emerald-500/30 text-emerald-400"
                : "bg-slate-900 border-slate-800 text-slate-400"
            }`}>
              <Icon className="w-4 h-4 animate-float" />
            </div>
            <div>
              <h3 className="font-semibold text-sm text-white group-hover:text-blue-400 transition-colors">
                {name} Agent
              </h3>
              <span className="text-[10px] text-slate-500 font-medium tracking-wider uppercase">
                {role}
              </span>
            </div>
          </div>
          
          {/* Status Badge */}
          <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border ${statusColor}`}>
            {status === "tool_call" ? "Using Tool" : status}
          </span>
        </div>

        {/* Description */}
        <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
          {description}
        </p>
      </div>

      {/* Tools Footer */}
      <div className="border-t border-slate-900 pt-3 flex flex-wrap gap-1.5 items-center">
        <span className="text-[9px] text-slate-500 uppercase tracking-widest mr-1">Tools:</span>
        {tools.map((t, idx) => (
          <span key={idx} className="text-[10px] px-2 py-0.5 rounded bg-slate-900/80 text-slate-400 font-medium border border-slate-800/60">
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}
