export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// Utility for fetching JSON
async function def_fetch(endpoint: string, options: RequestInit = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
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
  async createTask(prompt: string, pluginName: string) {
    return def_fetch("/tasks", {
      method: "POST",
      body: JSON.stringify({ prompt, plugin_name: pluginName }),
    });
  },

  async getTasks() {
    return def_fetch("/tasks");
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

  // Agents
  async getAgents() {
    return def_fetch("/agents");
  },

  // Plugins
  async getPlugins() {
    return def_fetch("/plugins");
  },

  // Memory
  async getMemory(query: string = "", category: string = "") {
    const params = new URLSearchParams();
    if (query) params.append("query", query);
    if (category) params.append("category", category);
    const queryStr = params.toString() ? `?${params.toString()}` : "";
    return def_fetch(`/memory${queryStr}`);
  },

  async addMemory(content: string, category: string = "factual") {
    return def_fetch("/memory", {
      method: "POST",
      body: JSON.stringify({ content, category }),
    });
  },

  // MCP Servers
  async getMCPServers() {
    return def_fetch("/mcp/servers");
  },

  async addMCPServer(name: string, command: string, args: string[] = []) {
    return def_fetch("/mcp/servers", {
      method: "POST",
      body: JSON.stringify({ name, command, args }),
    });
  },

  async removeMCPServer(name: string) {
    return def_fetch(`/mcp/servers/${name}`, {
      method: "DELETE",
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
