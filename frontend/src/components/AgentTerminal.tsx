"use client";

import { useEffect, useRef, useState } from "react";
import { Terminal, ShieldAlert, CheckCircle, Info, ExternalLink } from "lucide-react";

interface LogEntry {
  id: number;
  task_id: string;
  subtask_id?: string;
  agent_name: string;
  log_type: string; // thinking, tool_call, output, error
  content: string;
  created_at: string;
}

interface AgentTerminalProps {
  logs: LogEntry[];
}

export default function AgentTerminal({ logs }: AgentTerminalProps) {
  const terminalEndRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    // Autoscroll to bottom of logs
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const filteredLogs = logs.filter(log => {
    if (filter === "all") return true;
    return log.log_type === filter;
  });

  const getLogColor = (type: string) => {
    switch (type) {
      case "thinking": return "text-blue-400";
      case "tool_call": return "text-amber-400";
      case "output": return "text-emerald-400";
      case "error": return "text-rose-400 font-semibold";
      default: return "text-slate-300";
    }
  };

  const getLogIcon = (type: string) => {
    switch (type) {
      case "thinking": return <Info className="w-3.5 h-3.5 inline mr-1.5 text-blue-500 shrink-0" />;
      case "tool_call": return <ExternalLink className="w-3.5 h-3.5 inline mr-1.5 text-amber-500 shrink-0" />;
      case "output": return <CheckCircle className="w-3.5 h-3.5 inline mr-1.5 text-emerald-500 shrink-0" />;
      case "error": return <ShieldAlert className="w-3.5 h-3.5 inline mr-1.5 text-rose-500 shrink-0" />;
      default: return null;
    }
  };

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-xl flex flex-col h-full overflow-hidden font-mono shadow-2xl">
      {/* Terminal Title Bar */}
      <div className="bg-slate-900 px-5 py-3 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Terminal className="w-4 h-4 text-blue-500" />
          <span className="text-xs text-slate-300 font-semibold uppercase tracking-wider">Live Agent Thinking Console</span>
        </div>
        
        {/* Terminal Controls */}
        <div className="flex items-center gap-2">
          <select 
            value={filter} 
            onChange={(e) => setFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800/60 rounded px-2.5 py-1 text-[11px] text-slate-400 focus:outline-none focus:border-slate-700"
          >
            <option value="all">All Channels</option>
            <option value="thinking">Thinking Logs</option>
            <option value="tool_call">Tool Executions</option>
            <option value="output">Outputs</option>
            <option value="error">Errors</option>
          </select>
        </div>
      </div>

      {/* Terminal Body */}
      <div className="flex-1 p-5 overflow-y-auto space-y-3.5 text-xs select-text">
        {filteredLogs.length === 0 ? (
          <div className="text-slate-600 italic h-full flex items-center justify-center">
            No live logs received. Start a workspace execution to stream thoughts.
          </div>
        ) : (
          filteredLogs.map((log) => (
            <div key={log.id} className="border-b border-slate-900/50 pb-2 flex gap-3 items-start hover:bg-slate-900/10 rounded px-1">
              <span className="text-[10px] text-slate-600 shrink-0 select-none">
                {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded shrink-0 bg-slate-900/80 border border-slate-800 ${getLogColor(log.log_type)}`}>
                    {log.agent_name}
                  </span>
                  <span className="text-[9px] text-slate-500 font-semibold uppercase tracking-wide">
                    {log.log_type}
                  </span>
                </div>
                <div className={`whitespace-pre-wrap leading-relaxed mt-1 text-[11px] ${log.log_type === "thinking" ? "text-slate-300" : log.log_type === "output" ? "text-slate-200" : getLogColor(log.log_type)}`}>
                  {getLogIcon(log.log_type)}
                  {log.content}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={terminalEndRef} />
      </div>
    </div>
  );
}
