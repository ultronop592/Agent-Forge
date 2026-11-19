"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Cpu, Plus, Trash2, Code2, Play, Hammer, X, Sparkles, Key, ShieldCheck, Globe, Database } from "lucide-react";
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

interface CatalogEntry {
  id: string;
  name: string;
  description: string;
  command: string;
  fixed_args: string[];
  pinned_package?: string;
  parameters: Record<string, any>;
  required_env: string[];
  needs_network: boolean;
}

export default function MCPControlDeck() {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  // In-memory admin key (NEVER persisted to localStorage or sessionStorage)
  const [adminKey, setAdminKey] = useState<string>("");

  // Catalog enablement modal state
  const [showCatalogModal, setShowCatalogModal] = useState(false);
  const [selectedCatalogId, setSelectedCatalogId] = useState<string>("");
  const [paramInputs, setParamInputs] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

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
      const [serversData, toolsData, catalogData] = await Promise.all([
        api.getMCPServers(),
        api.getMCPTools().catch(() => []),
        api.getMCPCatalog().catch(() => []),
      ]);
      setServers(serversData);
      setTools(toolsData);
      setCatalog(catalogData);
      if (catalogData.length > 0 && !selectedCatalogId) {
        setSelectedCatalogId(catalogData[0].id);
      }
    } catch (e) {
      console.error("Failed to load MCP data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 8000);
    return () => clearInterval(interval);
  }, []);

  const handleOpenCatalogModal = () => {
    setFormError(null);
    if (catalog.length > 0 && !selectedCatalogId) {
      setSelectedCatalogId(catalog[0].id);
    }
    setParamInputs({});
    setShowCatalogModal(true);
  };

  const handleEnableCatalogServer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCatalogId || isSubmitting) return;

    if (!adminKey.trim()) {
      setFormError("Admin Key is required to enable an MCP server.");
      return;
    }

    setIsSubmitting(true);
    setFormError(null);
    try {
      await api.enableMCPServer(selectedCatalogId, paramInputs, adminKey.trim());
      setShowCatalogModal(false);
      setParamInputs({});
      loadData();
    } catch (err: any) {
      setFormError(err instanceof Error ? err.message : String(err));
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
    if (!adminKey.trim()) {
      setDeleteError("Admin Key is required to remove an MCP server.");
      return;
    }

    setIsDeleting(true);
    setDeleteError(null);
    try {
      await api.removeMCPServer(serverToDelete.name, adminKey.trim());
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

  const activeCatalogEntry = catalog.find((c) => c.id === selectedCatalogId);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-9 w-full relative z-10 bg-[#121214] text-[#f4f4f5]">
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
        description="Are you sure you want to stop the subprocess and disconnect this Model Context Protocol server? Admin authentication is enforced."
        itemLabel={serverToDelete?.name}
        itemSubLabel={serverToDelete ? `Command: ${serverToDelete.command} ${serverToDelete.args}` : undefined}
        confirmText="Remove Server"
        isLoading={isDeleting}
        errorMessage={deleteError}
      />

      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-[#da7756]/15 border border-[#da7756]/30 text-[#da7756] flex items-center justify-center">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">
                Model Context Protocol (MCP) Control Deck
              </h2>
              <p className="text-zinc-400 text-xs mt-0.5">
                Vetted catalog enablement with subprocess hardening, resource boundaries, and administrative key separation.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-[#18181b] border border-zinc-800 rounded-xl px-3 py-1.5">
            <Key className="w-3.5 h-3.5 text-[#da7756]" />
            <input
              type="password"
              value={adminKey}
              onChange={(e) => setAdminKey(e.target.value)}
              placeholder="Admin Key (Memory only)"
              className="bg-transparent text-xs text-white placeholder-zinc-500 focus:outline-none w-44"
            />
          </div>

          <button
            onClick={handleOpenCatalogModal}
            className="px-4 py-2.5 rounded-xl bg-[#da7756] hover:bg-[#c96a4a] text-white text-xs font-bold flex items-center gap-2 transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Enable Catalog Server</span>
          </button>
        </div>
      </div>

      {/* Catalog Enablement Modal */}
      {showCatalogModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <form
            onSubmit={handleEnableCatalogServer}
            className="bg-[#18181b] border border-zinc-800 rounded-2xl p-6 w-full max-w-xl space-y-4 shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div className="flex items-center gap-2 text-white font-bold text-xs uppercase tracking-wider">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Enable Vetted Catalog MCP Server</span>
              </div>
              <button
                type="button"
                onClick={() => setShowCatalogModal(false)}
                className="p-1 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                {formError}
              </div>
            )}

            <div className="space-y-2">
              <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-bold">Select Catalog Entry</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {catalog.map((entry) => (
                  <button
                    key={entry.id}
                    type="button"
                    onClick={() => {
                      setSelectedCatalogId(entry.id);
                      setParamInputs({});
                    }}
                    className={`p-3 rounded-xl border text-left transition flex flex-col justify-between ${
                      selectedCatalogId === entry.id
                        ? "bg-[#da7756]/15 border-[#da7756] text-white"
                        : "bg-[#121214] border-zinc-800 text-zinc-400 hover:border-zinc-700"
                    }`}
                  >
                    <div>
                      <div className="font-bold text-xs flex items-center gap-1.5">
                        {entry.needs_network ? (
                          <Globe className="w-3.5 h-3.5 text-sky-400" />
                        ) : (
                          <Database className="w-3.5 h-3.5 text-emerald-400" />
                        )}
                        <span>{entry.name}</span>
                      </div>
                      <p className="text-[10px] text-zinc-400 mt-1 line-clamp-2">{entry.description}</p>
                    </div>
                    <span className="text-[9px] font-mono text-zinc-500 mt-2 block">
                      {entry.command} {entry.pinned_package || entry.fixed_args.join(" ")}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {activeCatalogEntry && Object.keys(activeCatalogEntry.parameters || {}).length > 0 && (
              <div className="space-y-3 border-t border-zinc-800 pt-3">
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-bold">
                  Configurable Parameters
                </label>
                {Object.entries(activeCatalogEntry.parameters).map(([key, schema]: [string, any]) => (
                  <div key={key} className="space-y-1">
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="text-zinc-300 font-mono">{key}</span>
                      <span className="text-zinc-500">{schema.description}</span>
                    </div>
                    <input
                      type="text"
                      value={paramInputs[key] || ""}
                      onChange={(e) => setParamInputs({ ...paramInputs, [key]: e.target.value })}
                      placeholder={schema.pattern ? `Pattern: ${schema.pattern}` : "Value"}
                      className="w-full bg-[#121214] border border-zinc-800 rounded-xl px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#da7756]/60 font-mono"
                    />
                  </div>
                ))}
              </div>
            )}

            {!adminKey.trim() && (
              <div className="space-y-1.5 border-t border-zinc-800 pt-3">
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-bold">Admin Secret Key</label>
                <input
                  type="password"
                  value={adminKey}
                  onChange={(e) => setAdminKey(e.target.value)}
                  placeholder="Enter X-Admin-Key"
                  className="w-full bg-[#121214] border border-zinc-800 rounded-xl px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#da7756]/60 font-mono"
                />
              </div>
            )}

            <div className="flex justify-end gap-2.5 text-xs pt-2">
              <button
                type="button"
                onClick={() => setShowCatalogModal(false)}
                className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 hover:text-white font-semibold cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !selectedCatalogId}
                className="px-5 py-2 rounded-xl bg-[#da7756] hover:bg-[#c96a4a] text-white font-bold disabled:opacity-40 transition-colors cursor-pointer"
              >
                {isSubmitting ? "Enabling..." : "Enable Server"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Main Grid: Server list (left) & Tools list (right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Servers list (span 5) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-300">
              Active Subprocess Servers
            </h3>
            <span className="text-[10px] text-zinc-500 font-semibold">{servers.length} Connected</span>
          </div>

          {loading ? (
            <div className="h-44 bg-[#141416] border border-zinc-800 rounded-2xl animate-pulse" />
          ) : servers.length === 0 ? (
            <div className="text-zinc-500 text-xs italic text-center p-8 bg-[#141416] border border-zinc-800 rounded-2xl">
              No MCP servers active. Click above to enable a vetted server from the catalog.
            </div>
          ) : (
            <div className="space-y-3.5">
              {servers.map((s) => (
                <div key={s.id} className="glass-panel-interactive border border-zinc-800 rounded-2xl p-5 space-y-3.5 relative overflow-hidden group bg-[#18181b]">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-bold text-sm text-white group-hover:text-[#da7756] transition-colors">{s.name}</h4>
                      <span className="text-[10px] text-zinc-400 font-mono block mt-0.5">{s.command} {s.args}</span>
                    </div>
                    <button
                      onClick={() => handleRequestRemoveServer(s)}
                      className="p-1.5 rounded-lg bg-[#121214] border border-zinc-800 hover:border-rose-500/40 text-zinc-500 hover:text-rose-400 transition cursor-pointer"
                      title="Remove MCP Server"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="border-t border-zinc-800 pt-3 flex items-center justify-between text-[10px] font-semibold text-zinc-400">
                    <div className="flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${s.status === "running" ? "bg-emerald-400" : "bg-rose-500"}`} />
                      <span className="capitalize">{s.status}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Hammer className="w-3.5 h-3.5 text-[#da7756]" />
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
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-300">
              Discovered Tools Directory
            </h3>
            <span className="text-[10px] text-zinc-500 font-semibold">{tools.length} Available</span>
          </div>

          {loading ? (
            <div className="h-72 bg-[#141416] border border-zinc-800 rounded-2xl animate-pulse" />
          ) : tools.length === 0 ? (
            <div className="text-zinc-500 text-xs italic text-center p-12 bg-[#141416] border border-zinc-800 rounded-2xl">
              No tools exposed. Enable a vetted catalog server to query capabilities.
            </div>
          ) : (
            <div className="space-y-3.5">
              {tools.map((t, idx) => (
                <div key={idx} className="glass-panel-interactive border border-zinc-800 rounded-2xl p-5 hover:border-[#da7756]/30 transition flex flex-col justify-between bg-[#18181b]">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-xs font-bold font-mono text-[#da7756]">{t.name}</h4>
                      <span className="text-[9px] uppercase font-bold text-zinc-400 px-2 py-0.5 rounded-md bg-[#121214] border border-zinc-800">
                        {t.mcp_server_name}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-300 leading-relaxed">{t.description}</p>
                  </div>

                  <div className="border-t border-zinc-800 pt-3 mt-3 flex justify-between items-center">
                    <span className="text-[10px] text-zinc-500 font-mono truncate max-w-xs">
                      Params: {Object.keys(t.inputSchema?.properties || {}).join(", ") || "None"}
                    </span>
                    <button
                      onClick={() => openToolTester(t)}
                      className="px-3.5 py-1.5 text-xs font-semibold bg-zinc-800 border border-zinc-700 hover:border-[#da7756]/40 rounded-xl text-zinc-300 hover:text-white flex items-center gap-1.5 transition cursor-pointer"
                    >
                      <Code2 className="w-3.5 h-3.5 text-[#da7756]" />
                      <span>Test Call</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Floating Tool Tester overlay modal */}
          {testingTool && (
            <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
              <div className="bg-[#18181b] border border-zinc-800 rounded-2xl p-6 w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl space-y-4">
                <div className="flex justify-between items-center border-b border-zinc-800 pb-3">
                  <div>
                    <h3 className="text-xs font-bold font-mono text-[#da7756]">{testingTool.name}</h3>
                    <span className="text-[10px] uppercase font-semibold text-zinc-500">Origin: {testingTool.mcp_server_name}</span>
                  </div>
                  <button
                    onClick={() => setTestingTool(null)}
                    className="p-1 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 overflow-hidden">
                  <div className="flex flex-col space-y-2 overflow-hidden h-full">
                    <label className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider">Arguments (JSON)</label>
                    <textarea
                      rows={12}
                      value={toolArgs}
                      onChange={(e) => setToolArgs(e.target.value)}
                      className="flex-1 w-full bg-[#121214] border border-zinc-800 rounded-xl p-3 text-xs text-white font-mono focus:outline-none focus:border-[#da7756]/60"
                    />
                    <button
                      onClick={handleTestTool}
                      disabled={testingProgress}
                      className="py-2.5 bg-[#da7756] hover:bg-[#c96a4a] disabled:opacity-40 text-white rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                    >
                      <Play className="w-3 h-3 fill-white" />
                      <span>Execute Tool Trigger</span>
                    </button>
                  </div>

                  <div className="flex flex-col space-y-2 overflow-hidden h-full">
                    <label className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider">Response payload</label>
                    <div className="flex-1 bg-[#121214] border border-zinc-800 rounded-xl p-3 overflow-y-auto font-mono text-[10px] text-zinc-300 whitespace-pre">
                      {testingProgress ? (
                        <div className="text-zinc-500 italic">Executing JSON-RPC request...</div>
                      ) : testResult ? (
                        JSON.stringify(testResult, null, 2)
                      ) : (
                        <div className="text-zinc-600 italic">Awaiting call execution...</div>
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
