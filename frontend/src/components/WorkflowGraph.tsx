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
  // Determine agent status
  const getAgentStatus = (agentKey: string): "idle" | "running" | "completed" => {
    if (taskStatus === "failed") return "idle";
    
    if (agentKey === "planner") {
      if (taskStatus === "pending") return "running";
      return "completed";
    }
    
    if (agentKey === "verifier") {
      if (taskStatus === "completed") return "completed";
      // Running if all non-verifier subtasks are completed and task is running
      const activeSubs = subtasks.filter(s => s.assigned_agent !== "verifier");
      if (activeSubs.length > 0 && activeSubs.every(s => s.status === "completed") && taskStatus === "running") {
        return "running";
      }
      return "idle";
    }

    // For specialized agents (researcher, reasoner, executor, memory_agent)
    const matchingSubs = subtasks.filter(s => s.assigned_agent === agentKey);
    if (matchingSubs.length === 0) return "idle";
    
    if (matchingSubs.some(s => s.status === "running")) return "running";
    if (matchingSubs.every(s => s.status === "completed")) return "completed";
    if (matchingSubs.some(s => s.status === "completed")) return "running"; // partially done
    
    return "idle";
  };

  const getBorderColor = (status: "idle" | "running" | "completed") => {
    if (status === "running") return "stroke-blue-500 stroke-[3px] filter drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]";
    if (status === "completed") return "stroke-emerald-500 stroke-[2px]";
    return "stroke-slate-800 stroke-[1.5px]";
  };

  const getBgColor = (status: "idle" | "running" | "completed") => {
    if (status === "running") return "fill-blue-950/90";
    if (status === "completed") return "fill-emerald-950/80";
    return "fill-slate-900/90";
  };

  const getTextColor = (status: "idle" | "running" | "completed") => {
    if (status === "running") return "fill-blue-400 font-semibold";
    if (status === "completed") return "fill-emerald-400";
    return "fill-slate-400";
  };

  const isEdgeActive = (fromStatus: "idle" | "running" | "completed", toStatus: "idle" | "running" | "completed") => {
    return fromStatus === "completed" && toStatus === "running";
  };

  // Node Positions (x, y)
  const nodes = {
    planner: { x: 80, y: 150, name: "Planner", role: "Decomposer", icon: Compass },
    researcher: { x: 240, y: 150, name: "Researcher", role: "Collector", icon: Search },
    memory: { x: 400, y: 50, name: "Memory", role: "Context recall", icon: FolderGit },
    reasoner: { x: 400, y: 150, name: "Reasoner", role: "Logic engine", icon: BrainCircuit },
    executor: { x: 560, y: 150, name: "Executor", role: "Author/Coder", icon: FileCode },
    verifier: { x: 720, y: 150, name: "Verifier", role: "QA Fact-Check", icon: ShieldCheck }
  };

  const s = {
    planner: getAgentStatus("planner"),
    researcher: getAgentStatus("researcher"),
    memory: getAgentStatus("memory_agent"),
    reasoner: getAgentStatus("reasoner"),
    executor: getAgentStatus("executor"),
    verifier: getAgentStatus("verifier")
  };

  return (
    <div className="glass-panel border border-slate-800 rounded-xl p-5 flex flex-col h-full overflow-hidden shadow-xl">
      <div className="flex items-center justify-between mb-4 border-b border-slate-900 pb-3">
        <h4 className="text-xs text-slate-300 font-semibold uppercase tracking-wider">
          Active Workforce Collaborative Graph
        </h4>
        <div className="flex items-center gap-4 text-[10px] text-slate-500 font-medium">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-slate-800 border border-slate-700" />
            <span>Idle</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            <span>Active Thinking</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Finished Node</span>
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center min-h-[220px]">
        <svg 
          viewBox="0 0 800 240" 
          className="w-full max-w-4xl h-auto"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Defs for Glow Filter */}
          <defs>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Connection Lines (Paths) */}
          
          {/* Planner -> Researcher */}
          <path 
            d={`M ${nodes.planner.x + 35} ${nodes.planner.y} L ${nodes.researcher.x - 35} ${nodes.researcher.y}`}
            className={`fill-none stroke-2 ${
              isEdgeActive(s.planner, s.researcher) 
                ? "stroke-blue-500 animate-pulse-flow" 
                : s.researcher === "completed" || s.researcher === "running" ? "stroke-emerald-600" : "stroke-slate-800"
            }`}
          />

          {/* Planner -> Memory */}
          <path 
            d={`M ${nodes.planner.x + 25} ${nodes.planner.y - 20} Q ${nodes.memory.x - 50} ${nodes.memory.y + 20} ${nodes.memory.x - 35} ${nodes.memory.y}`}
            className={`fill-none stroke-2 stroke-dashed ${
              s.memory === "completed" || s.memory === "running" ? "stroke-blue-600/60" : "stroke-slate-800/40"
            }`}
          />

          {/* Memory -> Researcher / Reasoner (Data Feed) */}
          <path 
            d={`M ${nodes.memory.x} ${nodes.memory.y + 25} L ${nodes.reasoner.x} ${nodes.reasoner.y - 35}`}
            className={`fill-none stroke-1.5 stroke-dashed ${
              s.memory === "completed" ? "stroke-emerald-600/50" : "stroke-slate-800/40"
            }`}
          />

          {/* Researcher -> Reasoner */}
          <path 
            d={`M ${nodes.researcher.x + 35} ${nodes.researcher.y} L ${nodes.reasoner.x - 35} ${nodes.reasoner.y}`}
            className={`fill-none stroke-2 ${
              isEdgeActive(s.researcher, s.reasoner) 
                ? "stroke-blue-500 animate-pulse-flow" 
                : s.reasoner === "completed" || s.reasoner === "running" ? "stroke-emerald-600" : "stroke-slate-800"
            }`}
          />

          {/* Reasoner -> Executor */}
          <path 
            d={`M ${nodes.reasoner.x + 35} ${nodes.reasoner.y} L ${nodes.executor.x - 35} ${nodes.executor.y}`}
            className={`fill-none stroke-2 ${
              isEdgeActive(s.reasoner, s.executor) 
                ? "stroke-blue-500 animate-pulse-flow" 
                : s.executor === "completed" || s.executor === "running" ? "stroke-emerald-600" : "stroke-slate-800"
            }`}
          />

          {/* Executor -> Verifier */}
          <path 
            d={`M ${nodes.executor.x + 35} ${nodes.executor.y} L ${nodes.verifier.x - 35} ${nodes.verifier.y}`}
            className={`fill-none stroke-2 ${
              isEdgeActive(s.executor, s.verifier) 
                ? "stroke-blue-500 animate-pulse-flow" 
                : s.verifier === "completed" ? "stroke-emerald-600" : "stroke-slate-800"
            }`}
          />

          {/* Verifier -> Memory (Record feedback loop) */}
          <path 
            d={`M ${nodes.verifier.x - 20} ${nodes.verifier.y - 20} Q ${nodes.memory.x + 50} ${nodes.memory.y + 20} ${nodes.memory.x + 35} ${nodes.memory.y}`}
            className={`fill-none stroke-1.5 stroke-dashed ${
              s.verifier === "completed" ? "stroke-emerald-500/45 animate-pulse-flow" : "stroke-slate-800/40"
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
                  className={`${getBgColor(status)} ${getBorderColor(status)} transition-all duration-500`}
                />
                
                {/* Lucide Icon Integration (Embedded SVG) */}
                <g transform="translate(-8, -8)" className={status === "running" ? "text-blue-400" : status === "completed" ? "text-emerald-400" : "text-slate-500"}>
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
                  className="text-[8px] fill-slate-500 tracking-wide"
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
