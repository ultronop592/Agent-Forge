"use client";

import { Compass, Search, BrainCircuit, FileCode, ShieldCheck, FolderGit, ShieldAlert } from "lucide-react";

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

    // Manager is "running" whenever any worker agent is running
    if (agentKey === "manager") {
      const workerAgents = ["researcher", "reasoner", "executor"];
      const anyRunning = subtasks.some(s => workerAgents.includes(s.assigned_agent) && s.status === "running");
      const anyDone    = subtasks.some(s => workerAgents.includes(s.assigned_agent) && s.status === "completed");
      if (taskStatus === "completed") return "completed";
      if (anyRunning || anyDone) return "running";
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
    if (status === "running")   return "stroke-blue-500 stroke-[3px] filter drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]";
    if (status === "completed") return "stroke-emerald-500 stroke-[2px]";
    return "stroke-slate-800 stroke-[1.5px]";
  };

  const getManagerBorderColor = (status: "idle" | "running" | "completed") => {
    if (status === "running")   return "stroke-amber-500 stroke-[3px] filter drop-shadow-[0_0_10px_rgba(245,158,11,0.6)]";
    if (status === "completed") return "stroke-amber-400 stroke-[2px]";
    return "stroke-slate-700 stroke-[1.5px]";
  };

  const getBgColor = (status: "idle" | "running" | "completed") => {
    if (status === "running")   return "fill-blue-950/90";
    if (status === "completed") return "fill-emerald-950/80";
    return "fill-slate-900/90";
  };

  const getManagerBgColor = (status: "idle" | "running" | "completed") => {
    if (status === "running")   return "fill-amber-950/90";
    if (status === "completed") return "fill-amber-950/70";
    return "fill-slate-900/80";
  };

  const getTextColor = (status: "idle" | "running" | "completed") => {
    if (status === "running")   return "fill-blue-400 font-semibold";
    if (status === "completed") return "fill-emerald-400";
    return "fill-slate-400";
  };

  const isEdgeActive = (fromStatus: "idle" | "running" | "completed", toStatus: "idle" | "running" | "completed") => {
    return fromStatus === "completed" && toStatus === "running";
  };

  // ── Node layout ────────────────────────────────────────────────────────
  // Worker row: y=175 (same as before)
  // Manager sits above the worker row at y=60, centred at x=460
  const workerY = 175;
  const managerX = 460;
  const managerY = 55;

  const nodes = {
    planner:    { x: 65,  y: workerY, name: "Planner",    role: "Decomposer",    icon: Compass },
    researcher: { x: 215, y: workerY, name: "Researcher", role: "Collector",     icon: Search },
    memory:     { x: 370, y: 80,      name: "Memory",     role: "Context recall", icon: FolderGit },
    reasoner:   { x: 370, y: workerY, name: "Reasoner",   role: "Logic engine",  icon: BrainCircuit },
    executor:   { x: 520, y: workerY, name: "Executor",   role: "Author/Coder",  icon: FileCode },
    verifier:   { x: 675, y: workerY, name: "Verifier",   role: "QA Fact-Check", icon: ShieldCheck },
  };

  const s = {
    planner:    getAgentStatus("planner"),
    researcher: getAgentStatus("researcher"),
    memory:     getAgentStatus("memory_agent"),
    reasoner:   getAgentStatus("reasoner"),
    executor:   getAgentStatus("executor"),
    verifier:   getAgentStatus("verifier"),
    manager:    getAgentStatus("manager"),
  };

  const managerStatus = s.manager;

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
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            <span>Manager Supervising</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Finished Node</span>
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center min-h-[260px]">
        <svg
          viewBox="0 0 750 270"
          className="w-full max-w-4xl h-auto"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            {/* Amber glow for Manager */}
            <filter id="amberglow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="5" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* ── Manager supervision dashed arcs to worker agents ── */}
          {/* Manager → Researcher */}
          <path
            d={`M ${managerX - 20} ${managerY + 25} Q ${nodes.researcher.x + 40} ${managerY - 10} ${nodes.researcher.x + 20} ${nodes.researcher.y - 28}`}
            className={`fill-none stroke-1 stroke-dashed ${
              managerStatus !== "idle" ? "stroke-amber-500/50 animate-pulse" : "stroke-slate-800/30"
            }`}
            strokeDasharray="4 4"
          />
          {/* Manager → Reasoner */}
          <path
            d={`M ${managerX} ${managerY + 28} L ${nodes.reasoner.x + 10} ${nodes.reasoner.y - 28}`}
            className={`fill-none stroke-1 ${
              managerStatus !== "idle" ? "stroke-amber-500/50" : "stroke-slate-800/30"
            }`}
            strokeDasharray="4 4"
          />
          {/* Manager → Executor */}
          <path
            d={`M ${managerX + 15} ${managerY + 25} Q ${nodes.executor.x - 20} ${managerY - 10} ${nodes.executor.x - 15} ${nodes.executor.y - 28}`}
            className={`fill-none stroke-1 ${
              managerStatus !== "idle" ? "stroke-amber-500/50" : "stroke-slate-800/30"
            }`}
            strokeDasharray="4 4"
          />

          {/* ── Standard pipeline edges ── */}

          {/* Planner → Researcher */}
          <path
            d={`M ${nodes.planner.x + 28} ${nodes.planner.y} L ${nodes.researcher.x - 28} ${nodes.researcher.y}`}
            className={`fill-none stroke-2 ${
              isEdgeActive(s.planner, s.researcher)
                ? "stroke-blue-500 animate-pulse-flow"
                : s.researcher !== "idle" ? "stroke-emerald-600" : "stroke-slate-800"
            }`}
          />

          {/* Planner → Memory (dashed) */}
          <path
            d={`M ${nodes.planner.x + 20} ${nodes.planner.y - 22} Q ${nodes.memory.x - 50} ${nodes.memory.y + 20} ${nodes.memory.x - 28} ${nodes.memory.y}`}
            className={`fill-none stroke-2 ${
              s.memory !== "idle" ? "stroke-blue-600/60" : "stroke-slate-800/40"
            }`}
            strokeDasharray="5 3"
          />

          {/* Memory → Reasoner */}
          <path
            d={`M ${nodes.memory.x} ${nodes.memory.y + 25} L ${nodes.reasoner.x} ${nodes.reasoner.y - 28}`}
            className={`fill-none stroke-1.5 ${
              s.memory === "completed" ? "stroke-emerald-600/50" : "stroke-slate-800/40"
            }`}
            strokeDasharray="4 3"
          />

          {/* Researcher → Reasoner */}
          <path
            d={`M ${nodes.researcher.x + 28} ${nodes.researcher.y} L ${nodes.reasoner.x - 28} ${nodes.reasoner.y}`}
            className={`fill-none stroke-2 ${
              isEdgeActive(s.researcher, s.reasoner)
                ? "stroke-blue-500 animate-pulse-flow"
                : s.reasoner !== "idle" ? "stroke-emerald-600" : "stroke-slate-800"
            }`}
          />

          {/* Reasoner → Executor */}
          <path
            d={`M ${nodes.reasoner.x + 28} ${nodes.reasoner.y} L ${nodes.executor.x - 28} ${nodes.executor.y}`}
            className={`fill-none stroke-2 ${
              isEdgeActive(s.reasoner, s.executor)
                ? "stroke-blue-500 animate-pulse-flow"
                : s.executor !== "idle" ? "stroke-emerald-600" : "stroke-slate-800"
            }`}
          />

          {/* Executor → Verifier */}
          <path
            d={`M ${nodes.executor.x + 28} ${nodes.executor.y} L ${nodes.verifier.x - 28} ${nodes.verifier.y}`}
            className={`fill-none stroke-2 ${
              isEdgeActive(s.executor, s.verifier)
                ? "stroke-blue-500 animate-pulse-flow"
                : s.verifier !== "idle" ? "stroke-emerald-600" : "stroke-slate-800"
            }`}
          />

          {/* Verifier → Memory (post-save dashed) */}
          <path
            d={`M ${nodes.verifier.x - 15} ${nodes.verifier.y - 20} Q ${nodes.memory.x + 55} ${nodes.memory.y + 25} ${nodes.memory.x + 28} ${nodes.memory.y}`}
            className={`fill-none stroke-1.5 ${
              s.verifier === "completed" ? "stroke-emerald-500/45 animate-pulse-flow" : "stroke-slate-800/40"
            }`}
            strokeDasharray="4 3"
          />

          {/* ── Manager node (amber, centred above worker row) ── */}
          <g transform={`translate(${managerX}, ${managerY})`}>
            {/* Outer glow ring when active */}
            {managerStatus !== "idle" && (
              <circle r="35" className="fill-amber-500/5 stroke-amber-500/20 stroke-[1px] animate-pulse" />
            )}
            <circle
              r="27"
              className={`${getManagerBgColor(managerStatus)} ${getManagerBorderColor(managerStatus)} transition-all duration-500`}
            />
            <g transform="translate(-8, -8)" className="text-amber-400">
              <foreignObject width="16" height="16">
                <ShieldAlert className="w-4 h-4" />
              </foreignObject>
            </g>
            <text y="43" textAnchor="middle" className="text-[10px] uppercase font-bold tracking-wider fill-amber-400">
              Manager
            </text>
            <text y="55" textAnchor="middle" className="text-[8px] fill-amber-600/80 tracking-wide">
              Supervisor
            </text>
          </g>

          {/* ── Worker nodes ── */}
          {Object.entries(nodes).map(([key, node]) => {
            const status = getAgentStatus(key === "memory" ? "memory_agent" : key);
            const IconComponent = node.icon;

            return (
              <g key={key} transform={`translate(${node.x}, ${node.y})`}>
                <circle
                  r="28"
                  className={`${getBgColor(status)} ${getBorderColor(status)} transition-all duration-500`}
                />
                <g
                  transform="translate(-8, -8)"
                  className={
                    status === "running"   ? "text-blue-400"
                    : status === "completed" ? "text-emerald-400"
                    : "text-slate-500"
                  }
                >
                  <foreignObject width="16" height="16">
                    <IconComponent className="w-4 h-4" />
                  </foreignObject>
                </g>
                <text
                  y="45"
                  textAnchor="middle"
                  className={`text-[10px] uppercase font-bold tracking-wider ${getTextColor(status)}`}
                >
                  {node.name}
                </text>
                <text y="57" textAnchor="middle" className="text-[8px] fill-slate-500 tracking-wide">
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
