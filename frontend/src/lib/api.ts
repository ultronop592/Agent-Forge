export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export interface PluginItem {
  plugin_id: string;
  name: string;
  description: string;
}

export const DEFAULT_PLUGINS: PluginItem[] = [
  {
    plugin_id: "software_debugging",
    name: "Software Debugging",
    description: "Diagnose stack traces, identify root-cause bugs, and generate verified code fixes."
  },
  {
    plugin_id: "general_analysis",
    name: "General Technical Analysis",
    description: "Multi-perspective technical tradeoff, architecture evaluation, and comprehensive research."
  },
  {
    plugin_id: "startup_research",
    name: "Startup Research & SWOT",
    description: "Grounded competitive intelligence, market sizing, industry analysis, and SWOT matrix."
  },
  {
    plugin_id: "code_review",
    name: "Code Health & Review",
    description: "Multi-dimensional static analysis, security auditing, and code maintainability review."
  },
  {
    plugin_id: "document_qa",
    name: "Document & Knowledge QA",
    description: "Knowledge extraction, policy verification, and structured Q&A from technical documents."
  }
];

export function getStoredApiKey(): string {
  if (typeof window !== "undefined") {
    return localStorage.getItem("agentforge_api_key") || "";
  }
  return "";
}

export function setStoredApiKey(key: string): void {
  if (typeof window !== "undefined") {
    if (key.trim()) {
      localStorage.setItem("agentforge_api_key", key.trim());
    } else {
      localStorage.removeItem("agentforge_api_key");
    }
  }
}

export function getEffectiveApiKey(): string {
  const stored = getStoredApiKey();
  if (stored) return stored;
  return process.env.NEXT_PUBLIC_API_KEY || "";
}

export interface HarnessUsage {
  step_count: number;
  max_steps: number;
  token_total: number;
  max_tokens: number;
  cost_total: number;
  max_cost_usd: number;
  elapsed_seconds: number;
  paused_seconds?: number;
  wall_seconds?: number;
  max_seconds: number;
  max_paused_seconds?: number;
}

// Utility for fetching JSON
async function def_fetch(endpoint: string, options: RequestInit = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const apiKey = getEffectiveApiKey();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(apiKey ? { "X-API-Key": apiKey } : {}),
    ...(options.headers as Record<string, string>),
  };
  const response = await fetch(url, {
    headers,
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }
  return response.json();
}

export const api = {
  // Tasks
  async createTask(prompt: string, pluginName: string, idempotencyKey?: string) {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers["Idempotency-Key"] = idempotencyKey;
    }
    return def_fetch("/tasks", {
      method: "POST",
      headers,
      body: JSON.stringify({ prompt, plugin_name: pluginName }),
    });
  },

  async retryTask(taskId: string, idempotencyKey?: string) {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers["Idempotency-Key"] = idempotencyKey;
    }
    return def_fetch(`/tasks/${taskId}/retry`, {
      method: "POST",
      headers,
    });
  },

  async getTasks(skip?: number, limit?: number) {
    const params = new URLSearchParams();
    if (skip !== undefined) params.append("skip", String(skip));
    if (limit !== undefined) params.append("limit", String(limit));
    const qs = params.toString();
    return def_fetch(`/tasks${qs ? `?${qs}` : ""}`);
  },

  async getTask(taskId: string) {
    return def_fetch(`/tasks/${taskId}`);
  },

  async deleteTask(taskId: string) {
    return def_fetch(`/tasks/${taskId}`, {
      method: "DELETE",
    });
  },

  async approvePlan(taskId: string, subtasks?: Array<{ title: string; description?: string; assigned_agent?: string }>) {
    return def_fetch(`/tasks/${taskId}/approve_plan`, {
      method: "POST",
      body: JSON.stringify({ subtasks }),
    });
  },

  async steerTask(taskId: string, steeringPrompt: string = "", action: "steer" | "force_complete" = "steer") {
    return def_fetch(`/tasks/${taskId}/steer`, {
      method: "POST",
      body: JSON.stringify({ steering_prompt: steeringPrompt, action }),
    });
  },

  async rejectTask(taskId: string, reason: string = "") {
    return def_fetch(`/tasks/${taskId}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },

  async getLogs(taskId: string) {
    return def_fetch(`/tasks/${taskId}/logs`);
  },

  getStreamUrl(taskId: string): string {
    return `${API_BASE_URL}/tasks/${taskId}/stream`;
  },

  getExportUrl(taskId: string, format: "md" | "pdf" | "zip"): string {
    return `${API_BASE_URL}/tasks/${taskId}/export?format=${format}`;
  },

  /** Trigger a file download for the given export format */
  async downloadExport(taskId: string, format: "md" | "pdf" | "zip"): Promise<void> {
    const apiKey = getEffectiveApiKey();
    const res = await fetch(`${API_BASE_URL}/tasks/${taskId}/export?format=${format}`, {
      headers: apiKey ? { "X-API-Key": apiKey } : {},
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Export failed: ${res.status}`);
    }
    const disposition = res.headers.get("Content-Disposition") || "";
    const filenameMatch = disposition.match(/filename="?([^";]+)"?/);
    const filename = filenameMatch ? filenameMatch[1] : `agentforge_export.${format}`;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  // Agents
  async getAgents() {
    return def_fetch("/agents");
  },

  async getAgentConfigs() {
    return def_fetch("/agents/config");
  },

  async getAgentConfig(agentName: string) {
    return def_fetch(`/agents/config/${agentName}`);
  },

  async updateAgentConfig(agentName: string, config: { model?: string; temperature?: number; token_budget?: number; custom_instruction?: string }) {
    return def_fetch(`/agents/config/${agentName}`, {
      method: "PUT",
      body: JSON.stringify(config),
    });
  },

  async updateBulkAgentConfigs(configs: Record<string, any>) {
    return def_fetch("/agents/config", {
      method: "PUT",
      body: JSON.stringify({ configs }),
    });
  },

  async resetAgentConfigs() {
    return def_fetch("/agents/config/reset", {
      method: "POST",
    });
  },

  // Plugins
  async getPlugins(): Promise<PluginItem[]> {
    try {
      const data = await def_fetch("/plugins");
      if (Array.isArray(data) && data.length > 0) {
        return data;
      }
      return DEFAULT_PLUGINS;
    } catch (e) {
      console.warn("Could not fetch plugins from server, using default plugins:", e);
      return DEFAULT_PLUGINS;
    }
  },

  // Memory
  async getMemory(query: string = "", category: string = "") {
    const params = new URLSearchParams();
    if (query) params.append("query", query);
    if (category) params.append("category", category);
    const queryStr = params.toString() ? `?${params.toString()}` : "";
    return def_fetch(`/memory${queryStr}`);
  },

  async getMemoryStats() {
    return def_fetch("/memory/stats");
  },

  async addMemory(content: string, category: string = "factual") {
    return def_fetch("/memory", {
      method: "POST",
      body: JSON.stringify({ content, category }),
    });
  },

  async deleteMemory(memoryId: string) {
    return def_fetch(`/memory/${memoryId}`, {
      method: "DELETE",
    });
  },

  async clearMemories(category?: string) {
    const params = new URLSearchParams();
    if (category && category !== "all") params.append("category", category);
    const queryStr = params.toString() ? `?${params.toString()}` : "";
    return def_fetch(`/memory${queryStr}`, {
      method: "DELETE",
    });
  },

  // MCP Servers
  async getMCPCatalog() {
    return def_fetch("/mcp/catalog");
  },

  async getMCPServers() {
    return def_fetch("/mcp/servers");
  },

  async enableMCPServer(catalogId: string, parameters: Record<string, any> = {}, adminKey?: string) {
    const headers: Record<string, string> = {};
    if (adminKey) {
      headers["X-Admin-Key"] = adminKey;
    }
    return def_fetch("/mcp/servers", {
      method: "POST",
      headers,
      body: JSON.stringify({ catalog_id: catalogId, parameters }),
    });
  },

  async addMCPServer(name: string, command: string, args: string[] = [], adminKey?: string) {
    const headers: Record<string, string> = {};
    if (adminKey) {
      headers["X-Admin-Key"] = adminKey;
    }
    return def_fetch("/mcp/servers", {
      method: "POST",
      headers,
      body: JSON.stringify({ name, command, args }),
    });
  },

  async removeMCPServer(name: string, adminKey?: string) {
    const headers: Record<string, string> = {};
    if (adminKey) {
      headers["X-Admin-Key"] = adminKey;
    }
    return def_fetch(`/mcp/servers/${name}`, {
      method: "DELETE",
      headers,
    });
  },

  async getMCPTools() {
    return def_fetch("/mcp/tools");
  },

  async callMCPTool(serverName: string, toolName: string, args: Record<string, any>) {
    return def_fetch("/mcp/tools/call", {
      method: "POST",
      body: JSON.stringify({
        server_name: serverName,
        tool_name: toolName,
        arguments: args,
      }),
    });
  },
};
