"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Cpu, Plus, Trash2, Code2, Play, CheckCircle2, AlertTriangle, Hammer } from "lucide-react";

interface MCPServer {
  id: string;
  name: string;
  transport: string;
  command: string;
  args: string;
  status: string; // running, stopped
  tools_count: number;
}

interface MCPTool {
  name: string;
  description: string;
  inputSchema: Record<string, any>;
  mcp_server_name: string;
}

export default function MCPControlDeck() {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [loading, setLoading] = useState(true);

  // Connection form state
  const [name, setName] = useState("");
  const [command, setCommand] = useState("");
  const [argsInput, setArgsInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showForm, setShowForm] = useState(false);

  // Tool tester state
  const [testingTool, setTestingTool] = useState<MCPTool | null>(null);
  const [toolArgs, setToolArgs] = useState("");
  const [testResult, setTestResult] = useState<any>(null);
  const [testingProgress, setTestingProgress] = useState(false);

  const loadData = async () => {
    try {
      const [serversData, toolsData] = await Promise.all([
        api.getMCPServers(),
        api.getMCPTools().catch(() => [])
      ]);
      setServers(serversData);
      setTools(toolsData);
    } catch (e) {
      console.error("Failed to load MCP servers:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 8000);
    return () => clearInterval(interval);
  }, []);

  const handleAddServer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !command.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      // Split args by space, taking quotes into account
      const args = argsInput.trim() 
        ? argsInput.match(/(?:[^\s"']+|"[^"]*"|'[^']*')+/g)?.map(s => s.replace(/['"]/g, "")) || []
        : [];
        
      await api.addMCPServer(name, command, args);
      setName("");
      setCommand("");
      setArgsInput("");
      setShowForm(false);
      loadData();
    } catch (err) {
      console.error("Failed to register server:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemoveServer = async (serverName: string) => {
    if (!confirm(`Are you sure you want to stop and remove MCP server '${serverName}'?`)) return;
    try {
      await api.removeMCPServer(serverName);
      loadData();
    } catch (err) {
      console.error("Failed to remove server:", err);
    }
  };

  const openToolTester = (tool: MCPTool) => {
    setTestingTool(tool);
    setTestResult(null);
    
    // Generate default args based on schema
    const defaultArgs: Record<string, any> = {};
    if (tool.inputSchema?.properties) {
      Object.entries(tool.inputSchema.properties).forEach(([key, prop]: [string, any]) => {
        defaultArgs[key] = prop.type === "string" ? "" : prop.type === "number" ? 0 : false;
      });
    }
    setToolArgs(JSON.stringify(defaultArgs, null, 2));
  };

  const handleTestTool = async () => {
    if (!testingTool || testingProgress) return;
    setTestingProgress(true);
    setTestResult(null);
    try {
      const parsedArgs = toolArgs.trim() ? JSON.parse(toolArgs) : {};
      const res = await api.callMCPTool(testingTool.mcp_server_name, testingTool.name, parsedArgs);
      setTestResult(res);
    } catch (e: any) {
      setTestResult({ error: e.message || "Failed to trigger tool call" });
    } finally {
      setTestingProgress(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-9 w-full relative z-10">
      
      {/* Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-900 pb-6">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2.5">
            <Cpu className="w-6 h-6 text-blue-500" />
            <span>Model Context Protocol (MCP) Control</span>
          </h2>
          <p className="text-slate-400 text-xs mt-1">
            Connect standard MCP JSON-RPC servers to dynamically expand the tools library accessible by the Research and Execution agents.
          </p>
        </div>
        
        <button 
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow transition"
        >
          <Plus className="w-4 h-4" />
          <span>Connect MCP Server</span>
        </button>
      </div>

      {/* Connect Server Form */}
      {showForm && (
        <form onSubmit={handleAddServer} className="glass-panel border border-slate-800 rounded-xl p-5 space-y-4 max-w-2xl">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider border-b border-slate-900 pb-2">
            Configure Stdio Subprocess Server
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Unique Server Name</label>
              <input 
                type="text" 
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. filesystem-server"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-350 focus:outline-none"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Binary Command</label>
              <input 
                type="text" 
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                placeholder="e.g. npx, python, node"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-350 focus:outline-none"
              />
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Arguments list</label>
            <input 
              type="text" 
              value={argsInput}
              onChange={(e) => setArgsInput(e.target.value)}
              placeholder='e.g. -y @modelcontextprotocol/server-filesystem "c:/kaggle ai agent/sandbox"'
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-350 focus:outline-none font-mono"
            />
          </div>
          <div className="flex justify-end gap-2 text-xs">
            <button 
              type="button" 
              onClick={() => setShowForm(false)} 
              className="px-3.5 py-1.5 rounded hover:bg-slate-900 text-slate-400 font-medium"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              disabled={isSubmitting || !name.trim() || !command.trim()}
              className="px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium shadow disabled:opacity-50"
            >
              Initialize Handshake
            </button>
          </div>
        </form>
      )}

      {/* Main Grid: Server list (left) & Tools list (right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Servers list (span 5) */}
        <div className="lg:col-span-5 space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Registered Subprocess Connections
          </h3>
          
          {loading ? (
            <div className="h-44 bg-slate-900/40 rounded-xl animate-pulse" />
          ) : servers.length === 0 ? (
            <div className="text-slate-500 text-xs italic text-center p-8 bg-slate-950 border border-slate-900 rounded-xl">
              No MCP servers connected.
            </div>
          ) : (
            <div className="space-y-4">
              {servers.map((s) => (
                <div key={s.id} className="glass-panel border border-slate-800 rounded-xl p-5 space-y-3.5 relative overflow-hidden group">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-semibold text-sm text-slate-100">{s.name}</h4>
                      <span className="text-[10px] text-slate-500 font-mono block mt-0.5">{s.command} {s.args}</span>
                    </div>
                    <button 
                      onClick={() => handleRemoveServer(s.name)}
                      className="p-1.5 rounded bg-slate-900 border border-slate-800 hover:border-rose-500/30 text-slate-500 hover:text-rose-400 transition"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <div className="border-t border-slate-900 pt-3 flex items-center justify-between text-[10px] font-semibold text-slate-500">
                    <div className="flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${s.status === "running" ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
                      <span className="capitalize">{s.status}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Hammer className="w-3.5 h-3.5 text-slate-650" />
                      <span>{s.tools_count} Tools Exposed</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Tools list & Tester (span 7) */}
        <div className="lg:col-span-7 space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Discovered Tools Directory
          </h3>

          {loading ? (
            <div className="h-72 bg-slate-900/40 rounded-xl animate-pulse" />
          ) : tools.length === 0 ? (
            <div className="text-slate-500 text-xs italic text-center p-12 bg-slate-950 border border-slate-900 rounded-xl">
              No tools exposed. Launch an active MCP server stdio pipeline above to query capabilities.
            </div>
          ) : (
            <div className="space-y-4">
              {tools.map((t, idx) => (
                <div key={idx} className="glass-panel border border-slate-800 rounded-xl p-5 hover:border-slate-700/60 transition duration-200 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-xs font-bold font-mono text-blue-400">{t.name}</h4>
                      <span className="text-[9px] uppercase font-bold text-slate-500 px-2 py-0.5 rounded bg-slate-900 border border-slate-850">
                        {t.mcp_server_name}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 leading-normal">{t.description}</p>
                  </div>
                  
                  <div className="border-t border-slate-900 pt-3 mt-3 flex justify-between items-center">
                    <span className="text-[10px] text-slate-500 font-mono">
                      Params: {Object.keys(t.inputSchema?.properties || {}).join(", ") || "None"}
                    </span>
                    <button
                      onClick={() => openToolTester(t)}
                      className="px-3 py-1 text-[10px] font-semibold bg-slate-900 border border-slate-800 hover:border-blue-500/30 rounded text-slate-300 hover:text-blue-400 flex items-center gap-1.5 transition cursor-pointer"
                    >
                      <Code2 className="w-3.5 h-3.5" />
                      <span>Test Call</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Floating Tool Tester overlay modal */}
          {testingTool && (
            <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
              <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-6 w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl space-y-4">
                <div className="flex justify-between items-center border-b border-slate-900 pb-3">
                  <div>
                    <h3 className="text-xs font-bold font-mono text-blue-400">{testingTool.name}</h3>
                    <span className="text-[9px] uppercase font-bold text-slate-500">Origin: {testingTool.mcp_server_name}</span>
                  </div>
                  <button 
                    onClick={() => setTestingTool(null)}
                    className="text-slate-500 hover:text-white text-sm font-semibold"
                  >
                    Close
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 overflow-hidden">
                  {/* Left: Args input */}
                  <div className="flex flex-col space-y-2 overflow-hidden h-full">
                    <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Arguments (JSON)</label>
                    <textarea 
                      rows={12}
                      value={toolArgs}
                      onChange={(e) => setToolArgs(e.target.value)}
                      className="flex-1 w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-300 font-mono focus:outline-none focus:border-blue-500"
                    />
                    <button 
                      onClick={handleTestTool}
                      disabled={testingProgress}
                      className="py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded font-semibold text-xs flex items-center justify-center gap-1.5 transition cursor-pointer"
                    >
                      <Play className="w-3 h-3 fill-white" />
                      <span>Execute Tool Trigger</span>
                    </button>
                  </div>

                  {/* Right: Output result */}
                  <div className="flex flex-col space-y-2 overflow-hidden h-full">
                    <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Response payload</label>
                    <div className="flex-1 bg-slate-950 border border-slate-850 rounded-lg p-3 overflow-y-auto font-mono text-[10px] text-slate-400 whitespace-pre">
                      {testingProgress ? (
                        <div className="text-slate-500 italic">Executing JSON-RPC request...</div>
                      ) : testResult ? (
                        JSON.stringify(testResult, null, 2)
                      ) : (
                        <div className="text-slate-600 italic">Awaiting call...</div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>

      </div>

    </div>
  );
}
