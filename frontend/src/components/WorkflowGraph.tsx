"use client";

import { Compass, Search, BrainCircuit, FileCode, ShieldCheck, FolderGit } from "lucide-react";

interface Subtask {
  id: string;
  task_id: string;
  title: string;
  assigned_agent: string;
  status: "pending" | "running" | "completed" | "failed";
}

interface WorkflowGraphProps {
  subtasks: Subtask[];
  taskStatus: string;
}

export default function WorkflowGraph({ subtasks, taskStatus }: WorkflowGraphProps) {
  const getAgentStatus = (agentKey: string): "idle" | "running" | "completed" => {
    if (taskStatus === "failed") return "idle";
    
    if (agentKey === "planner") {
      if (taskStatus === "pending") return "running";
      return "completed";
    }
    
    if (agentKey === "verifier") {
      if (taskStatus === "completed") return "completed";
      const activeSubs = subtasks.filter(s => s.assigned_agent !== "verifier");
      if (activeSubs.length > 0 && activeSubs.every(s => s.status === "completed") && taskStatus === "running") {
        return "running";
      }
      return "idle";
    }

    const matchingSubs = subtasks.filter(s => s.assigned_agent === agentKey);
    if (matchingSubs.length === 0) return "idle";
    
    if (matchingSubs.some(s => s.status === "running")) return "running";
    if (matchingSubs.every(s => s.status === "completed")) return "completed";
    if (matchingSubs.some(s => s.status === "completed")) return "running";
    
    return "idle";
  };

  const getBorderColor = (status: "idle" | "running" | "completed") => {
    if (status === "running") return "stroke-[#da7756] stroke-[2.5px]";
    if (status === "completed") return "stroke-emerald-500 stroke-[2px]";
    return "stroke-zinc-800 stroke-[1.5px]";
  };

  const getBgColor = (status: "idle" | "running" | "completed") => {
    if (status === "running") return "fill-[#251c19]";
    if (status === "completed") return "fill-[#14221a]";
    return "fill-[#18181b]";
  };

  const getTextColor = (status: "idle" | "running" | "completed") => {
    if (status === "running") return "fill-[#da7756] font-bold";
    if (status === "completed") return "fill-emerald-400 font-semibold";
    return "fill-zinc-400";
  };

  const isEdgeActive = (fromStatus: "idle" | "running" | "completed", toStatus: "idle" | "running" | "completed") => {
    return fromStatus === "completed" && toStatus === "running";
  };

  const nodes = {
    planner: { x: 90, y: 150, name: "Planner", role: "Decomposer", icon: Compass },
    analyst: { x: 250, y: 150, name: "Analyst", role: "Search & Reason", icon: Search },
    memory: { x: 410, y: 50, name: "Memory", role: "Vector Recall", icon: FolderGit },
    executor: { x: 410, y: 150, name: "Executor", role: "Code & Report", icon: FileCode },
    verifier: { x: 570, y: 150, name: "Verifier", role: "QA Fact-Check", icon: ShieldCheck }
  };

  const s = {
    planner: getAgentStatus("planner"),
    analyst: getAgentStatus("analyst"),
    memory: getAgentStatus("memory_agent"),
    executor: getAgentStatus("executor"),
    verifier: getAgentStatus("verifier")
  };

  return (
    <div className="glass-panel-elevated rounded-2xl p-6 flex flex-col h-full overflow-hidden border border-zinc-800 bg-[#18181b]">
      <div className="flex items-center justify-between mb-4 border-b border-zinc-800 pb-3.5">
        <div className="flex items-center gap-3">
          <h4 className="text-xs text-white font-bold uppercase tracking-wider">
            Autonomous Workforce Dynamic Graph
          </h4>
          <span className="px-2.5 py-0.5 rounded-full bg-[#da7756]/10 border border-[#da7756]/30 text-[10px] font-bold text-[#da7756] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#da7756]" />
            Manager Orchestrated
          </span>
        </div>
        
        <div className="flex items-center gap-4 text-[10px] text-zinc-400 font-semibold">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-zinc-800 border border-zinc-700" />
            <span>Idle</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#da7756]" />
            <span className="text-[#da7756]">Active Thinking</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-emerald-400">Completed Node</span>
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center min-h-[240px] relative">
        <svg 
          viewBox="0 0 660 240" 
          className="w-full max-w-3xl h-auto select-none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Connection Lines (Paths) */}
          
          {/* Planner -> Analyst */}
          <path 
            d={`M ${nodes.planner.x + 35} ${nodes.planner.y} L ${nodes.analyst.x - 35} ${nodes.analyst.y}`}
            className={`fill-none stroke-2 ${
              isEdgeActive(s.planner, s.analyst) 
                ? "stroke-[#da7756] animate-pulse-flow" 
                : s.analyst === "completed" || s.analyst === "running" ? "stroke-emerald-500" : "stroke-zinc-800"
            }`}
          />

          {/* Planner -> Memory */}
          <path 
            d={`M ${nodes.planner.x + 25} ${nodes.planner.y - 20} Q ${nodes.memory.x - 50} ${nodes.memory.y + 20} ${nodes.memory.x - 35} ${nodes.memory.y}`}
            className={`fill-none stroke-2 stroke-dashed ${
              s.memory === "completed" || s.memory === "running" ? "stroke-[#da7756]/70" : "stroke-zinc-800/50"
            }`}
          />

          {/* Memory -> Analyst */}
          <path 
            d={`M ${nodes.memory.x} ${nodes.memory.y + 25} L ${nodes.analyst.x + 10} ${nodes.analyst.y - 35}`}
            className={`fill-none stroke-1.5 stroke-dashed ${
              s.memory === "completed" ? "stroke-emerald-500/60" : "stroke-zinc-800/50"
            }`}
          />

          {/* Analyst -> Executor */}
          <path 
            d={`M ${nodes.analyst.x + 35} ${nodes.analyst.y} L ${nodes.executor.x - 35} ${nodes.executor.y}`}
            className={`fill-none stroke-2 ${
              isEdgeActive(s.analyst, s.executor) 
                ? "stroke-[#da7756] animate-pulse-flow" 
                : s.executor === "completed" || s.executor === "running" ? "stroke-emerald-500" : "stroke-zinc-800"
            }`}
          />

          {/* Executor -> Verifier */}
          <path 
            d={`M ${nodes.executor.x + 35} ${nodes.executor.y} L ${nodes.verifier.x - 35} ${nodes.verifier.y}`}
            className={`fill-none stroke-2 ${
              isEdgeActive(s.executor, s.verifier) 
                ? "stroke-[#da7756] animate-pulse-flow" 
                : s.verifier === "completed" ? "stroke-emerald-500" : "stroke-zinc-800"
            }`}
          />

          {/* Verifier -> Memory */}
          <path 
            d={`M ${nodes.verifier.x - 20} ${nodes.verifier.y - 20} Q ${nodes.memory.x + 50} ${nodes.memory.y + 20} ${nodes.memory.x + 35} ${nodes.memory.y}`}
            className={`fill-none stroke-1.5 stroke-dashed ${
              s.verifier === "completed" ? "stroke-emerald-400/60 animate-pulse-flow" : "stroke-zinc-800/50"
            }`}
          />

          {/* Render Nodes */}
          {Object.entries(nodes).map(([key, node]) => {
            const status = getAgentStatus(key === "memory" ? "memory_agent" : key);
            const IconComponent = node.icon;
            
            return (
              <g key={key} transform={`translate(${node.x}, ${node.y})`}>
                {/* Node Ring */}
                <circle 
                  r="28" 
                  className={`${getBgColor(status)} ${getBorderColor(status)} transition-all duration-300`}
                />
                
                {/* Lucide Icon Integration */}
                <g transform="translate(-8, -8)" className={status === "running" ? "text-[#da7756]" : status === "completed" ? "text-emerald-400" : "text-zinc-400"}>
                  <foreignObject width="16" height="16">
                    <IconComponent className="w-4 h-4" />
                  </foreignObject>
                </g>

                {/* Node Labels */}
                <text 
                  y="45" 
                  textAnchor="middle" 
                  className={`text-[10px] uppercase font-bold tracking-wider ${getTextColor(status)}`}
                >
                  {node.name}
                </text>
                <text 
                  y="57" 
                  textAnchor="middle" 
                  className="text-[8px] fill-zinc-500 font-medium tracking-wide"
                >
                  {node.role}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
