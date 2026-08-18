"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Cpu, Plus, Trash2, Code2, Play, CheckCircle2, AlertTriangle, Hammer, X, Sparkles } from "lucide-react";
import DeleteConfirmModal from "@/components/DeleteConfirmModal";

interface MCPServer {
  id: string;
  name: string;
  transport: string;
  command: string;
  args: string;
  status: string;
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

  // Deletion modal state
  const [serverToDelete, setServerToDelete] = useState<MCPServer | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

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

  const handleRequestRemoveServer = (server: MCPServer) => {
    setDeleteError(null);
    setServerToDelete(server);
  };

  const handleConfirmRemoveServer = async () => {
    if (!serverToDelete) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await api.removeMCPServer(serverToDelete.name);
      setServerToDelete(null);
      loadData();
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsDeleting(false);
    }
  };

  const openToolTester = (tool: MCPTool) => {
    setTestingTool(tool);
    setTestResult(null);
    
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
      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={!!serverToDelete}
        onClose={() => {
          if (!isDeleting) {
            setServerToDelete(null);
            setDeleteError(null);
          }
        }}
        onConfirm={handleConfirmRemoveServer}
        title="Remove MCP Server"
        description="Are you sure you want to stop the subprocess and disconnect this Model Context Protocol server? Any tools exposed by this server will no longer be callable."
        itemLabel={serverToDelete?.name}
        itemSubLabel={serverToDelete ? `Command: ${serverToDelete.command} ${serverToDelete.args}` : undefined}
        confirmText="Remove Server"
        isLoading={isDeleting}
        errorMessage={deleteError}
      />

      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-sky-500/15 border border-sky-500/30 text-sky-400 flex items-center justify-center">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">
                Model Context Protocol (MCP) Control Deck
              </h2>
              <p className="text-slate-400 text-xs mt-0.5">
                Connect standard MCP JSON-RPC servers to dynamically expand the tool capabilities accessible by autonomous agents.
              </p>
            </div>
          </div>
        </div>
        
        <button 
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-sky-950/40 glow-primary transition cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Connect MCP Server</span>
        </button>
      </div>

      {/* Connect Server Form */}
      {showForm && (
        <form onSubmit={handleAddServer} className="glass-panel-elevated rounded-2xl p-6 space-y-4 max-w-2xl border border-sky-500/30">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2 text-white font-bold text-xs uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-sky-400" />
              <span>Configure Stdio Subprocess Server</span>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-[10px] text-slate-400 uppercase tracking-wider font-bold">Unique Server Name</label>
              <input 
                type="text" 
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. filesystem-server"
                className="w-full bg-[#080b12] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500/60"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] text-slate-400 uppercase tracking-wider font-bold">Binary Command</label>
              <input 
                type="text" 
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                placeholder="e.g. npx, python, node"
                className="w-full bg-[#080b12] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500/60"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] text-slate-400 uppercase tracking-wider font-bold">Arguments list</label>
            <input 
              type="text" 
              value={argsInput}
              onChange={(e) => setArgsInput(e.target.value)}
              placeholder='e.g. -y @modelcontextprotocol/server-filesystem "c:/sandbox"'
              className="w-full bg-[#080b12] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500/60 font-mono"
            />
          </div>
          <div className="flex justify-end gap-2.5 text-xs pt-1">
            <button 
              type="button" 
              onClick={() => setShowForm(false)} 
              className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white font-semibold cursor-pointer"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              disabled={isSubmitting || !name.trim() || !command.trim()}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold shadow-lg shadow-emerald-950/40 disabled:opacity-50 cursor-pointer"
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
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Registered Subprocess Connections
            </h3>
            <span className="text-[10px] text-slate-500 font-semibold">{servers.length} Connected</span>
          </div>
          
          {loading ? (
            <div className="h-44 bg-[#080b12] border border-slate-800 rounded-2xl animate-pulse" />
          ) : servers.length === 0 ? (
            <div className="text-slate-500 text-xs italic text-center p-8 bg-[#080b12] border border-slate-800 rounded-2xl">
              No MCP servers connected. Click above to connect a stdio server.
            </div>
          ) : (
            <div className="space-y-3.5">
              {servers.map((s) => (
                <div key={s.id} className="glass-panel-interactive border border-slate-800/90 rounded-2xl p-5 space-y-3.5 relative overflow-hidden group">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-bold text-sm text-white group-hover:text-sky-300 transition-colors">{s.name}</h4>
                      <span className="text-[10px] text-slate-400 font-mono block mt-0.5">{s.command} {s.args}</span>
                    </div>
                    <button 
                      onClick={() => handleRequestRemoveServer(s)}
                      className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-rose-500/40 text-slate-500 hover:text-rose-400 transition cursor-pointer"
                      title="Remove MCP Server"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  
                  <div className="border-t border-slate-800/80 pt-3 flex items-center justify-between text-[10px] font-semibold text-slate-400">
                    <div className="flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${s.status === "running" ? "bg-emerald-400 pulse-emerald" : "bg-rose-500"}`} />
                      <span className="capitalize">{s.status}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Hammer className="w-3.5 h-3.5 text-sky-400" />
                      <span>{s.tools_count} Tools Discovered</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Tools list & Tester (span 7) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Discovered Tools Directory
            </h3>
            <span className="text-[10px] text-slate-500 font-semibold">{tools.length} Available</span>
          </div>

          {loading ? (
            <div className="h-72 bg-[#080b12] border border-slate-800 rounded-2xl animate-pulse" />
          ) : tools.length === 0 ? (
            <div className="text-slate-500 text-xs italic text-center p-12 bg-[#080b12] border border-slate-800 rounded-2xl">
              No tools exposed. Launch an active MCP server stdio pipeline to query capabilities.
            </div>
          ) : (
            <div className="space-y-3.5">
              {tools.map((t, idx) => (
                <div key={idx} className="glass-panel-interactive border border-slate-800/90 rounded-2xl p-5 hover:border-sky-500/30 transition flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-xs font-bold font-mono text-sky-300">{t.name}</h4>
                      <span className="text-[9px] uppercase font-bold text-slate-400 px-2 py-0.5 rounded-md bg-[#05070c] border border-slate-800">
                        {t.mcp_server_name}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">{t.description}</p>
                  </div>
                  
                  <div className="border-t border-slate-800/80 pt-3 mt-3 flex justify-between items-center">
                    <span className="text-[10px] text-slate-500 font-mono truncate max-w-xs">
                      Params: {Object.keys(t.inputSchema?.properties || {}).join(", ") || "None"}
                    </span>
                    <button
                      onClick={() => openToolTester(t)}
                      className="px-3.5 py-1.5 text-xs font-semibold bg-slate-900 border border-slate-800 hover:border-sky-500/40 rounded-xl text-slate-300 hover:text-white flex items-center gap-1.5 transition cursor-pointer"
                    >
                      <Code2 className="w-3.5 h-3.5 text-sky-400" />
                      <span>Test Call</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Floating Tool Tester overlay modal */}
          {testingTool && (
            <div className="fixed inset-0 bg-[#07090e]/80 backdrop-blur-md flex items-center justify-center p-4 z-50">
              <div className="bg-[#090d16] border border-slate-800 rounded-2xl p-6 w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl space-y-4">
                <div className="flex justify-between items-center border-b border-slate-800 pb-3">
                  <div>
                    <h3 className="text-xs font-bold font-mono text-sky-400">{testingTool.name}</h3>
                    <span className="text-[10px] uppercase font-semibold text-slate-500">Origin: {testingTool.mcp_server_name}</span>
                  </div>
                  <button 
                    onClick={() => setTestingTool(null)}
                    className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 overflow-hidden">
                  {/* Left: Args input */}
                  <div className="flex flex-col space-y-2 overflow-hidden h-full">
                    <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Arguments (JSON)</label>
                    <textarea 
                      rows={12}
                      value={toolArgs}
                      onChange={(e) => setToolArgs(e.target.value)}
                      className="flex-1 w-full bg-[#05070c] border border-slate-800 rounded-xl p-3 text-xs text-white font-mono focus:outline-none focus:border-sky-500/60"
                    />
                    <button 
                      onClick={handleTestTool}
                      disabled={testingProgress}
                      className="py-2.5 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 disabled:opacity-50 text-white rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 transition cursor-pointer shadow-lg shadow-sky-950/40"
                    >
                      <Play className="w-3 h-3 fill-white" />
                      <span>Execute Tool Trigger</span>
                    </button>
                  </div>

                  {/* Right: Output result */}
                  <div className="flex flex-col space-y-2 overflow-hidden h-full">
                    <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Response payload</label>
                    <div className="flex-1 bg-[#05070c] border border-slate-800 rounded-xl p-3 overflow-y-auto font-mono text-[10px] text-slate-300 whitespace-pre">
                      {testingProgress ? (
                        <div className="text-slate-500 italic">Executing JSON-RPC request...</div>
                      ) : testResult ? (
                        JSON.stringify(testResult, null, 2)
                      ) : (
                        <div className="text-slate-600 italic">Awaiting call execution...</div>
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
