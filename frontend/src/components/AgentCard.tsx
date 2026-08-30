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
  agent: {
    name: string;
    role: string;
    status: "idle" | "thinking" | "tool_call" | "completed" | "failed";
    description: string;
    tools: string[];
  };
}

const AGENT_ICONS: Record<string, any> = {
  "Planner": Compass,
  "Manager": Layers,
  "Analyst": Search,
  "Researcher": Search,
  "Reasoner": BrainCircuit,
  "Executor": FileCode,
  "Verifier": ShieldCheck,
  "MemoryAgent": FolderGit,
  "Memory": FolderGit
};

const STATUS_COLORS: Record<string, string> = {
  idle: "bg-zinc-800/80 text-zinc-400 border-zinc-700/60",
  thinking: "bg-[#da7756]/15 text-[#da7756] border-[#da7756]/30",
  tool_call: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  completed: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  failed: "bg-rose-500/15 text-rose-300 border-rose-500/30"
};

export default function AgentCard({ agent }: AgentCardProps) {
  const { name, role, status, description, tools } = agent;
  const Icon = AGENT_ICONS[name] || BrainCircuit;
  const statusBadge = STATUS_COLORS[status] || STATUS_COLORS.idle;

  return (
    <div className="glass-panel-interactive rounded-2xl p-5 flex flex-col justify-between h-48 relative overflow-hidden group border border-zinc-800/90 bg-[#18181b]">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center border transition-all ${
              status === "thinking"
                ? "bg-[#da7756]/15 border-[#da7756]/40 text-[#da7756]"
                : status === "completed"
                ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-300"
                : "bg-[#121214] border-zinc-800 text-zinc-400 group-hover:text-[#da7756] group-hover:border-[#da7756]/30"
            }`}>
              <Icon className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-white group-hover:text-[#da7756] transition-colors">
                {name} Agent
              </h3>
              <span className="text-[10px] text-zinc-400 font-semibold tracking-wider uppercase">
                {role}
              </span>
            </div>
          </div>
          
          {/* Status Badge */}
          <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${statusBadge}`}>
            {status === "tool_call" ? "Tool Invocation" : status}
          </span>
        </div>

        {/* Description */}
        <p className="text-xs text-zinc-400 line-clamp-2 leading-relaxed">
          {description}
        </p>
      </div>

      {/* Tools Footer */}
      <div className="border-t border-zinc-800/80 pt-3 flex flex-wrap gap-1.5 items-center">
        <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider mr-1">Tools:</span>
        {tools && tools.length > 0 ? (
          tools.map((t, idx) => (
            <span key={idx} className="text-[10px] px-2 py-0.5 rounded-md bg-[#121214] text-zinc-300 font-medium border border-zinc-800">
              {t}
            </span>
          ))
        ) : (
          <span className="text-[10px] text-zinc-500 italic">Built-in LLM Reasoning</span>
        )}
      </div>
    </div>
  );
}
