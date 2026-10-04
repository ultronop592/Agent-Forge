"use client";

import { useEffect, useState, useMemo } from "react";
import { api } from "@/lib/api";
import { 
  Sliders, 
  Cpu, 
  Bot, 
  Zap, 
  Thermometer, 
  Coins, 
  RotateCcw, 
  Save, 
  Check, 
  AlertCircle, 
  Sparkles, 
  Layers, 
  Info, 
  ShieldCheck, 
  Compass, 
  Search, 
  FileCode, 
  BrainCircuit, 
  Users,
  Activity,
  CheckCheck
} from "lucide-react";

interface AgentConfig {
  model: string;
  temperature: number;
  token_budget: number;
  custom_instruction?: string;
}

interface ModelOption {
  id: string;
  name: string;
  badge: string;
  description: string;
  context_window: string;
  speed: string;
  input_cost_per_m: string;
  output_cost_per_m: string;
}

const AGENTS_LIST = [
  { id: "global", name: "Global Defaults", role: "Workforce Default", icon: Layers, desc: "Default fallback parameters applied to all agents unless specifically overridden below." },
  { id: "Planner", name: "Planner Agent", role: "Lead Architect", icon: Compass, desc: "Decomposes goals into structured subtask chains with deterministic milestones." },
  { id: "Analyst", name: "Analyst Agent", role: "Research & SWOT", icon: Search, desc: "Conducts live Tavily intelligence gathering and multi-dimensional SWOT synthesis." },
  { id: "Researcher", name: "Researcher Agent", role: "Web Intelligence", icon: Search, desc: "Extracts grounded web facts and technical references with verifiable citations." },
  { id: "Reasoner", name: "Reasoner Agent", role: "Logic & Architecture", icon: BrainCircuit, desc: "Applies chain-of-thought analysis to isolate root causes and outline solutions." },
  { id: "Executor", name: "Executor Agent", role: "Deliverable Builder", icon: FileCode, desc: "Synthesizes production-quality code, technical guides, or strategic reports." },
  { id: "Verifier", name: "Verifier Agent", role: "QA Judge & Fact-Checker", icon: ShieldCheck, desc: "LLM-as-a-Judge validation engine checking deliverable accuracy against requirements." },
  { id: "Manager", name: "Manager Agent", role: "Orchestration Supervisor", icon: Users, desc: "Supervises pipeline transitions, tracks agent quality scores, and writes run summaries." },
  { id: "MemoryAgent", name: "Memory Agent", role: "Institutional Recall", icon: BrainCircuit, desc: "Stores vector embeddings and recalls historic context via Cosine Vector Search." },
];

export default function SettingsPage() {
  const [configs, setConfigs] = useState<Record<string, AgentConfig>>({});
  const [availableModels, setAvailableModels] = useState<ModelOption[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>("global");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Form states for the currently selected agent
  const [model, setModel] = useState<string>("gemini-2.5-flash");
  const [temperature, setTemperature] = useState<number>(0.2);
  const [tokenBudget, setTokenBudget] = useState<number>(3000);
  const [customInstruction, setCustomInstruction] = useState<string>("");
  const [isInheritedModel, setIsInheritedModel] = useState<boolean>(true);

  const showToast = (message: string, type: "success" | "error" = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3500);
  };

  const loadConfigs = async () => {
    setLoading(true);
    try {
      const data = await api.getAgentConfigs();
      if (data && data.configs) {
        setConfigs(data.configs);
        if (data.available_models) {
          setAvailableModels(data.available_models);
        }
      }
    } catch (e) {
      console.error("Failed to load agent configurations:", e);
      showToast("Failed to load settings from server", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfigs();
  }, []);

  // Whenever selectedAgent or configs changes, populate form values
  useEffect(() => {
    if (!configs) return;
    const globalCfg = configs["global"] || { model: "gemini-2.5-flash", temperature: 0.2, token_budget: 3000, custom_instruction: "" };
    const currentCfg = configs[selectedAgent] || {};

    if (selectedAgent === "global") {
      setModel(currentCfg.model || "gemini-2.5-flash");
      setTemperature(currentCfg.temperature ?? 0.2);
      setTokenBudget(currentCfg.token_budget ?? 3000);
      setCustomInstruction(currentCfg.custom_instruction || "");
      setIsInheritedModel(false);
    } else {
      const specificModel = currentCfg.model;
      if (specificModel && specificModel.trim() !== "") {
        setModel(specificModel);
        setIsInheritedModel(false);
      } else {
        setModel(globalCfg.model || "gemini-2.5-flash");
        setIsInheritedModel(true);
      }
      setTemperature(currentCfg.temperature ?? globalCfg.temperature ?? 0.2);
      setTokenBudget(currentCfg.token_budget ?? globalCfg.token_budget ?? 3000);
      setCustomInstruction(currentCfg.custom_instruction || "");
    }
  }, [selectedAgent, configs]);

  // Handle Save
  const handleSave = async () => {
    setSaving(true);
    try {
      const payload: { model?: string; temperature: number; token_budget: number; custom_instruction: string } = {
        model: isInheritedModel && selectedAgent !== "global" ? "" : model,
        temperature: Number(temperature),
        token_budget: Number(tokenBudget),
        custom_instruction: customInstruction.trim()
      };

      await api.updateAgentConfig(selectedAgent, payload);

      // Update in-memory state
      setConfigs((prev) => ({
        ...prev,
        [selectedAgent]: {
          ...prev[selectedAgent],
          ...payload
        }
      }));

      // If global model updated, refresh all
      if (selectedAgent === "global") {
        await loadConfigs();
      }

      showToast(`Configuration saved for ${selectedAgent === "global" ? "Global Defaults" : selectedAgent}`);
    } catch (err) {
      console.error("Failed to save configuration:", err);
      showToast("Error saving configuration", "error");
    } finally {
      setSaving(false);
    }
  };

  // Handle Reset to Defaults
  const handleReset = async () => {
    if (!confirm("Reset all agent parameters to platform factory defaults?")) return;
    setSaving(true);
    try {
      const data = await api.resetAgentConfigs();
      if (data && data.data && data.data.configs) {
        setConfigs(data.data.configs);
      } else {
        await loadConfigs();
      }
      showToast("Factory defaults restored");
    } catch (err) {
      console.error("Failed to reset configurations:", err);
      showToast("Failed to reset configurations", "error");
    } finally {
      setSaving(false);
    }
  };

  // Temperature description helper
  const getTemperatureNote = (temp: number) => {
    if (temp <= 0.05) return "Deterministic & Exact: Zero randomness. Ideal for code generation, syntax validation, and factual QA.";
    if (temp <= 0.3) return "Focused & Structured (Recommended): Low variance with disciplined reasoning. Ideal for analytical tasks and architecture design.";
    if (temp <= 0.6) return "Balanced: Moderate creativity and fluency while respecting constraints.";
    return "Creative & Exploratory: High diversity of phrasing. Ideal for brainstorming, strategy narratives, and creative writing.";
  };

  // Estimated max cost calculation
  const selectedModelMeta = availableModels.find((m) => m.id === model) || availableModels[0];
  const estimatedCostPerCall = useMemo(() => {
    if (!selectedModelMeta) return "$0.0009";
    const outRate = parseFloat(selectedModelMeta.output_cost_per_m.replace("$", "")) || 0.30;
    const est = (tokenBudget / 1_000_000) * outRate;
    return `$${est.toFixed(5)}`;
  }, [selectedModelMeta, tokenBudget]);

  const activeAgentMeta = AGENTS_LIST.find((a) => a.id === selectedAgent) || AGENTS_LIST[0];
  const ActiveIcon = activeAgentMeta.icon;

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 w-full relative z-10 bg-[#121214] text-[#f4f4f5]">
      {/* Toast Notification */}
      {toast && (
        <div 
          className={`fixed top-6 right-6 z-50 px-4 py-2.5 rounded-xl border text-xs font-semibold shadow-2xl flex items-center gap-2 backdrop-blur-md transition-all ${
            toast.type === "success"
              ? "bg-emerald-950/80 border-emerald-500/50 text-emerald-200"
              : "bg-rose-950/80 border-rose-500/50 text-rose-200"
          }`}
        >
          {toast.type === "success" ? (
            <Check className="w-4 h-4 text-emerald-400" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-400" />
          )}
          <span>{toast.message}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#da7756]/15 border border-[#da7756]/30 text-[#da7756] flex items-center justify-center shrink-0">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-white tracking-tight">
                  Agent Configuration & Tuning Panel
                </h1>
                <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-md bg-[#da7756]/15 border border-[#da7756]/30 text-[#da7756]">
                  Live Control
                </span>
              </div>
              <p className="text-zinc-400 text-xs mt-1">
                Customize Gemini foundation models, sampling temperature, and token budgets per workforce role in real-time.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 self-start md:self-auto">
          <button
            onClick={handleReset}
            disabled={saving}
            className="px-3.5 py-2 rounded-xl border border-zinc-800 bg-[#161619] hover:bg-zinc-800 text-zinc-400 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Defaults</span>
          </button>
          
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-2 rounded-xl bg-[#da7756] hover:bg-[#c96a4a] text-white text-xs font-bold flex items-center gap-2 transition cursor-pointer shadow-lg shadow-[#da7756]/15 disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{saving ? "Saving..." : "Save Settings"}</span>
          </button>
        </div>
      </div>

      {/* Two Column Layout: Left Agent Navigation, Right Configuration Form */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-7 items-start">
        {/* Left Agent Selector Column (4 cols) */}
        <div className="lg:col-span-4 space-y-2">
          <div className="text-[11px] font-bold uppercase tracking-wider text-zinc-500 px-1 mb-2">
            Workforce Role Selector
          </div>

          <div className="space-y-1.5 bg-[#161619] border border-zinc-800/80 rounded-2xl p-2.5">
            {AGENTS_LIST.map((agent) => {
              const Icon = agent.icon;
              const isSelected = selectedAgent === agent.id;
              const agentCfg = configs[agent.id] || {};
              const currentModel = agent.id === "global" 
                ? (agentCfg.model || "gemini-2.5-flash") 
                : (agentCfg.model && agentCfg.model.trim() !== "" ? agentCfg.model : `${configs["global"]?.model || "gemini-2.5-flash"} (inherited)`);

              return (
                <button
                  key={agent.id}
                  onClick={() => setSelectedAgent(agent.id)}
                  className={`w-full text-left p-3 rounded-xl transition-all cursor-pointer flex items-center justify-between gap-3 ${
                    isSelected
                      ? "bg-[#da7756]/15 border border-[#da7756]/40 text-white shadow-sm"
                      : "hover:bg-zinc-800/60 border border-transparent text-zinc-400 hover:text-white"
                  }`}
                >
                  <div className="flex items-center gap-2.5 overflow-hidden">
                    <div className={`p-1.5 rounded-lg shrink-0 ${
                      isSelected ? "bg-[#da7756] text-white" : "bg-zinc-800/80 text-zinc-400"
                    }`}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div className="overflow-hidden">
                      <div className="text-xs font-bold truncate text-white">
                        {agent.name}
                      </div>
                      <div className="text-[10px] text-zinc-500 truncate">
                        {agent.role}
                      </div>
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-zinc-800/90 border border-zinc-700/50 text-zinc-300 block">
                      T: {agentCfg.temperature !== undefined ? agentCfg.temperature : 0.2}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Configuration Form Column (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {/* Active Agent Banner */}
          <div className="border border-zinc-800/90 bg-[#161619] rounded-2xl p-5 flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-[#da7756]/15 border border-[#da7756]/30 text-[#da7756] flex items-center justify-center shrink-0">
              <ActiveIcon className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white tracking-tight">
                  {activeAgentMeta.name}
                </h2>
                <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-md bg-zinc-800 border border-zinc-700 text-zinc-300">
                  {activeAgentMeta.role}
                </span>
              </div>
              <p className="text-zinc-400 text-xs mt-1 leading-relaxed">
                {activeAgentMeta.desc}
              </p>
            </div>
          </div>

          {/* Form Settings Card */}
          <div className="border border-zinc-800/90 bg-[#161619] rounded-2xl p-6 space-y-7">
            {/* 1. Model Selection */}
            <div className="space-y-3.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-[#da7756]" />
                  <label className="text-xs font-bold uppercase tracking-wider text-white">
                    Foundation Model
                  </label>
                </div>

                {selectedAgent !== "global" && (
                  <label className="flex items-center gap-2 text-xs text-zinc-400 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={isInheritedModel}
                      onChange={(e) => {
                        const checked = e.target.checked;
                        setIsInheritedModel(checked);
                        if (checked) {
                          setModel(configs["global"]?.model || "gemini-2.5-flash");
                        }
                      }}
                      className="w-3.5 h-3.5 rounded border-zinc-700 bg-[#121214] text-[#da7756] accent-[#da7756]"
                    />
                    <span>Inherit Global ({configs["global"]?.model || "gemini-2.5-flash"})</span>
                  </label>
                )}
              </div>

              {/* Models Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {availableModels.map((m) => {
                  const isChosen = model === m.id && (!isInheritedModel || selectedAgent === "global");
                  return (
                    <div
                      key={m.id}
                      onClick={() => {
                        setModel(m.id);
                        setIsInheritedModel(false);
                      }}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer flex flex-col justify-between space-y-2 ${
                        isChosen
                          ? "border-[#da7756] bg-[#da7756]/10 shadow-sm ring-1 ring-[#da7756]/40"
                          : "border-zinc-800 bg-[#121214] hover:border-zinc-700 hover:bg-[#151518]"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-xs text-white">{m.name}</span>
                          <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${
                            isChosen ? "bg-[#da7756]/20 border-[#da7756]/40 text-[#da7756]" : "bg-zinc-800 border-zinc-700 text-zinc-400"
                          }`}>
                            {m.badge}
                          </span>
                        </div>
                        {isChosen && <Check className="w-3.5 h-3.5 text-[#da7756]" />}
                      </div>

                      <p className="text-[11px] text-zinc-400 leading-snug">
                        {m.description}
                      </p>

                      <div className="flex items-center justify-between text-[10px] text-zinc-500 font-mono border-t border-zinc-800/80 pt-2">
                        <span>Window: {m.context_window}</span>
                        <span>Output: {m.output_cost_per_m}/M</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 2. Temperature Slider */}
            <div className="space-y-3.5 border-t border-zinc-800/80 pt-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Thermometer className="w-4 h-4 text-[#da7756]" />
                  <label className="text-xs font-bold uppercase tracking-wider text-white">
                    Sampling Temperature
                  </label>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-[#da7756] bg-[#da7756]/15 border border-[#da7756]/30 px-2.5 py-0.5 rounded-lg">
                    {temperature.toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Slider Input */}
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-[#da7756]"
              />

              {/* Preset Chips */}
              <div className="flex items-center gap-2 flex-wrap">
                {[
                  { label: "0.00 Deterministic", val: 0.0 },
                  { label: "0.10 Precise", val: 0.1 },
                  { label: "0.20 Balanced", val: 0.2 },
                  { label: "0.50 Moderate", val: 0.5 },
                  { label: "0.75 Creative", val: 0.75 },
                ].map((p) => (
                  <button
                    key={p.val}
                    type="button"
                    onClick={() => setTemperature(p.val)}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition cursor-pointer ${
                      Math.abs(temperature - p.val) < 0.01
                        ? "bg-[#da7756]/20 border-[#da7756]/50 text-white"
                        : "border-zinc-800 bg-[#121214] text-zinc-400 hover:text-white hover:border-zinc-700"
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>

              {/* Dynamic Temperature Behavior Note */}
              <p className="text-[11px] text-zinc-400 bg-[#121214] border border-zinc-800 rounded-xl p-3 leading-relaxed">
                💡 <span className="text-zinc-200 font-semibold">{getTemperatureNote(temperature)}</span>
              </p>
            </div>

            {/* 3. Token Budget Ceiling */}
            <div className="space-y-3.5 border-t border-zinc-800/80 pt-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Coins className="w-4 h-4 text-[#da7756]" />
                  <label className="text-xs font-bold uppercase tracking-wider text-white">
                    Max Output Token Budget Ceiling
                  </label>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-zinc-400">Est. max call cost:</span>
                  <span className="font-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-lg">
                    {estimatedCostPerCall}
                  </span>
                </div>
              </div>

              {/* Presets and Custom Input */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
                {[
                  { label: "Small", tokens: 1500, note: "Quick facts / bug fixes" },
                  { label: "Medium", tokens: 3000, note: "Structured code / review" },
                  { label: "Large", tokens: 6000, note: "Full reports & modules" },
                  { label: "XL Deep", tokens: 10000, note: "Full system memos" }
                ].map((tier) => {
                  const isTier = tokenBudget === tier.tokens;
                  return (
                    <button
                      key={tier.tokens}
                      type="button"
                      onClick={() => setTokenBudget(tier.tokens)}
                      className={`p-3 rounded-xl border text-left transition cursor-pointer ${
                        isTier 
                          ? "bg-[#da7756]/15 border-[#da7756] text-white" 
                          : "border-zinc-800 bg-[#121214] text-zinc-400 hover:text-white hover:border-zinc-700"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-white">{tier.label}</span>
                        {isTier && <Check className="w-3 h-3 text-[#da7756]" />}
                      </div>
                      <div className="font-mono text-xs font-bold text-[#da7756] mt-0.5">
                        {tier.tokens.toLocaleString()} tokens
                      </div>
                      <div className="text-[10px] text-zinc-500 mt-1 leading-snug">
                        {tier.note}
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Numeric Input */}
              <div className="flex items-center gap-3">
                <span className="text-xs text-zinc-400 whitespace-nowrap">Exact Token Cap:</span>
                <input
                  type="number"
                  min="250"
                  max="32000"
                  step="250"
                  value={tokenBudget}
                  onChange={(e) => setTokenBudget(Math.max(250, parseInt(e.target.value) || 250))}
                  className="w-36 bg-[#121214] border border-zinc-800 rounded-xl px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-[#da7756]/60"
                />
                <span className="text-[11px] text-zinc-500">
                  (Limits maximum completion length for {selectedAgent})
                </span>
              </div>
            </div>

            {/* 4. Custom Directives Textarea */}
            <div className="space-y-2.5 border-t border-zinc-800/80 pt-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-[#da7756]" />
                  <label className="text-xs font-bold uppercase tracking-wider text-white">
                    Custom Steering Directives (System Instruction Addendum)
                  </label>
                </div>
                <span className="text-[10px] text-zinc-500 font-mono">Optional</span>
              </div>

              <textarea
                rows={3}
                value={customInstruction}
                onChange={(e) => setCustomInstruction(e.target.value)}
                placeholder={`Inject specialized constraints or instructions for ${selectedAgent} (e.g. 'Ensure all outputs follow strict TypeScript typing and PEP8 syntax')...`}
                className="w-full bg-[#121214] border border-zinc-800 rounded-xl p-3.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#da7756]/60 leading-relaxed resize-none font-mono"
              />
            </div>
          </div>

          {/* Action Row */}
          <div className="flex items-center justify-end gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-2.5 rounded-xl bg-[#da7756] hover:bg-[#c96a4a] text-white text-xs font-bold flex items-center gap-2 transition cursor-pointer shadow-lg shadow-[#da7756]/15 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? "Saving Changes..." : `Save ${selectedAgent} Settings`}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Workforce Configuration Summary Matrix Table */}
      <div className="border border-zinc-800 bg-[#161619] rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-[#da7756]" />
            <h3 className="text-sm font-bold text-white tracking-tight">
              Workforce Configuration Summary Matrix
            </h3>
          </div>
          <span className="text-[11px] text-zinc-400">
            Real-time active values applied on next pipeline execution
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-zinc-800 text-[10px] font-bold uppercase text-zinc-500">
                <th className="py-2.5 px-3">Agent</th>
                <th className="py-2.5 px-3">Model</th>
                <th className="py-2.5 px-3">Temperature</th>
                <th className="py-2.5 px-3">Token Budget</th>
                <th className="py-2.5 px-3">Custom Directives</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 font-mono">
              {AGENTS_LIST.map((agent) => {
                const cfg = configs[agent.id] || {};
                const isSelected = selectedAgent === agent.id;
                const effectiveModel = agent.id === "global" 
                  ? (cfg.model || "gemini-2.5-flash") 
                  : (cfg.model && cfg.model.trim() !== "" ? cfg.model : `${configs["global"]?.model || "gemini-2.5-flash"}*`);

                return (
                  <tr 
                    key={agent.id}
                    className={`hover:bg-zinc-800/40 transition-colors ${isSelected ? "bg-[#da7756]/5" : ""}`}
                  >
                    <td className="py-3 px-3 font-sans font-bold text-white flex items-center gap-2">
                      <agent.icon className="w-3.5 h-3.5 text-[#da7756]" />
                      <span>{agent.name}</span>
                    </td>
                    <td className="py-3 px-3 text-zinc-300">
                      <span className="px-2 py-0.5 rounded bg-zinc-800/80 border border-zinc-700/60 text-[11px]">
                        {effectiveModel}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-[#da7756] font-bold">
                      {cfg.temperature !== undefined ? cfg.temperature.toFixed(2) : (configs["global"]?.temperature?.toFixed(2) || "0.20")}
                    </td>
                    <td className="py-3 px-3 text-emerald-400">
                      {(cfg.token_budget || configs["global"]?.token_budget || 3000).toLocaleString()}
                    </td>
                    <td className="py-3 px-3 text-zinc-400 truncate max-w-xs font-sans text-[11px]">
                      {cfg.custom_instruction ? cfg.custom_instruction : <span className="text-zinc-600 italic">None</span>}
                    </td>
                    <td className="py-3 px-3 text-right font-sans">
                      <button
                        onClick={() => setSelectedAgent(agent.id)}
                        className="px-2.5 py-1 rounded-lg border border-zinc-700 hover:border-[#da7756] bg-zinc-800 hover:bg-[#da7756]/15 hover:text-white text-[10px] font-semibold text-zinc-300 transition cursor-pointer"
                      >
                        Tune
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="text-[10px] text-zinc-500 font-sans italic">
          * Indicates model inherited from Global Default.
        </p>
      </div>
    </div>
  );
}
