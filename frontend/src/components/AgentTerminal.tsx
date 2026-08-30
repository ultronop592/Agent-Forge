"use client";

import { useEffect, useRef, useState } from "react";
import { Terminal, ShieldAlert, CheckCircle, Info, ExternalLink, Copy, Check } from "lucide-react";

interface LogEntry {
  id: number;
  task_id: string;
  subtask_id?: string;
  agent_name: string;
  log_type: string;
  content: string;
  created_at: string;
}

interface AgentTerminalProps {
  logs: LogEntry[];
  isStreaming?: boolean;
}

export default function AgentTerminal({ logs, isStreaming = false }: AgentTerminalProps) {
  const terminalEndRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<string>("all");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const filteredLogs = logs.filter(log => {
    if (filter === "all") return true;
    return log.log_type === filter;
  });

  const getLogColor = (type: string) => {
    switch (type) {
      case "thinking":         return "text-[#e08569]";
      case "tool_call":        return "text-amber-300";
      case "output":           return "text-emerald-300";
      case "error":            return "text-rose-400 font-semibold";
      case "manager_decision": return "text-amber-200 font-semibold";
      case "telemetry":        return "text-zinc-400";
      default: return "text-zinc-300";
    }
  };

  const getLogIcon = (type: string) => {
    switch (type) {
      case "thinking":         return <Info className="w-3.5 h-3.5 inline mr-1.5 text-[#da7756] shrink-0" />;
      case "tool_call":        return <ExternalLink className="w-3.5 h-3.5 inline mr-1.5 text-amber-400 shrink-0" />;
      case "output":           return <CheckCircle className="w-3.5 h-3.5 inline mr-1.5 text-emerald-400 shrink-0" />;
      case "error":            return <ShieldAlert className="w-3.5 h-3.5 inline mr-1.5 text-rose-400 shrink-0" />;
      case "manager_decision": return <ShieldAlert className="w-3.5 h-3.5 inline mr-1.5 text-amber-300 shrink-0" />;
      default: return null;
    }
  };

  const copyLogs = () => {
    const text = logs.map(l => `[${l.created_at}] [${l.agent_name}] [${l.log_type}]: ${l.content}`).join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-[#121214] border border-zinc-800 rounded-2xl flex flex-col h-full overflow-hidden font-mono">
      {/* Terminal Title Bar */}
      <div className="bg-[#161619] px-5 py-3 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          </div>
          <div className="flex items-center gap-2 pl-2 border-l border-zinc-800">
            <Terminal className="w-4 h-4 text-[#da7756]" />
            <span className="text-xs text-white font-bold uppercase tracking-wider">
              Thinking & Execution Console
            </span>
            {isStreaming && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-[9px] font-bold text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
                LIVE STREAM
              </span>
            )}
          </div>
        </div>
        
        {/* Terminal Controls */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={copyLogs}
            className="px-2.5 py-1 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 hover:text-white text-[10px] font-semibold flex items-center gap-1 transition cursor-pointer"
            title="Copy all logs"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>Copy Logs</span>
              </>
            )}
          </button>

          <select 
            value={filter} 
            onChange={(e) => setFilter(e.target.value)}
            className="bg-[#121214] border border-zinc-800 rounded-lg px-2.5 py-1 text-[10px] text-zinc-300 font-semibold focus:outline-none focus:border-[#da7756]/50 cursor-pointer"
          >
            <option value="all">All Channels ({logs.length})</option>
            <option value="thinking">Thinking Logs</option>
            <option value="tool_call">Tool Calls</option>
            <option value="output">Outputs</option>
            <option value="manager_decision">Decisions</option>
            <option value="telemetry">Telemetry</option>
            <option value="error">Errors</option>
          </select>
        </div>
      </div>

      {/* Terminal Body */}
      <div className="flex-1 p-5 overflow-y-auto space-y-3 text-xs select-text bg-[#121214]">
        {filteredLogs.length === 0 ? (
          <div className="text-zinc-500 italic h-full flex items-center justify-center text-xs">
            No logs matching filter. Launch a task to stream live agent reasoning.
          </div>
        ) : (
          filteredLogs.map((log) => (
            <div key={log.id} className="border-b border-zinc-800/60 pb-2.5 flex gap-3 items-start hover:bg-zinc-800/30 rounded-lg px-1.5 transition">
              <span className="text-[10px] text-zinc-500 shrink-0 select-none pt-0.5">
                {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <span className={`text-[9px] font-bold uppercase px-1.5 py-0.2 rounded shrink-0 bg-[#18181b] border border-zinc-800 ${getLogColor(log.log_type)}`}>
                    {log.agent_name}
                  </span>
                  <span className="text-[9px] text-zinc-500 font-semibold uppercase tracking-wider">
                    {log.log_type}
                  </span>
                </div>
                <div className={`whitespace-pre-wrap leading-relaxed mt-1 text-[11px] font-mono ${
                  log.log_type === "thinking" ? "text-zinc-300"
                  : log.log_type === "output" ? "text-zinc-200"
                  : log.log_type === "manager_decision" ? "text-amber-200 bg-amber-950/20 border border-amber-900/30 rounded-lg p-2"
                  : getLogColor(log.log_type)
                }`}>
                  {getLogIcon(log.log_type)}
                  {log.content}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={terminalEndRef} />
        {isStreaming && (
          <div className="flex items-center gap-2 pt-1 pb-1">
            <span className="text-[10px] text-zinc-500 select-none">—</span>
            <span className="w-2 h-3.5 bg-[#da7756] rounded-sm" />
          </div>
        )}
      </div>
    </div>
  );
}
