"""
agent_config.py
Manages dynamic agent parameters (temperature, model, token budget ceiling, custom directives)
both globally and per individual agent role.
"""

from typing import Dict, Any, List, Optional
import threading
from backend.app.core.config import settings

AVAILABLE_MODELS = [
    {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "badge": "Default & Fast",
        "description": "High-velocity, cost-effective reasoning. Recommended for standard pipelines.",
        "context_window": "1,048,576 tokens",
        "speed": "Fastest",
        "input_cost_per_m": "$0.075",
        "output_cost_per_m": "$0.30"
    },
    {
        "id": "gemini-2.5-pro",
        "name": "Gemini 2.5 Pro",
        "badge": "Deep Reasoning",
        "description": "State-of-the-art complex multi-step reasoning, intricate code synthesis, and deep analysis.",
        "context_window": "2,097,152 tokens",
        "speed": "Standard",
        "input_cost_per_m": "$1.25",
        "output_cost_per_m": "$5.00"
    },
    {
        "id": "gemini-1.5-pro",
        "name": "Gemini 1.5 Pro",
        "badge": "Massive Context",
        "description": "Long-context understanding, large document analysis, and comprehensive literature research.",
        "context_window": "2,097,152 tokens",
        "speed": "Standard",
        "input_cost_per_m": "$1.25",
        "output_cost_per_m": "$5.00"
    },
    {
        "id": "gemini-1.5-flash",
        "name": "Gemini 1.5 Flash",
        "badge": "Lightweight",
        "description": "Low-latency throughput for rapid validation, preliminary triage, and light queries.",
        "context_window": "1,048,576 tokens",
        "speed": "Fast",
        "input_cost_per_m": "$0.075",
        "output_cost_per_m": "$0.30"
    }
]

DEFAULT_AGENT_CONFIGS: Dict[str, Dict[str, Any]] = {
    "global": {
        "model": getattr(settings, "cost_model", "gemini-2.5-flash") or "gemini-2.5-flash",
        "temperature": 0.2,
        "token_budget": 3000,
        "custom_instruction": ""
    },
    "Planner": {
        "model": "",
        "temperature": 0.1,
        "token_budget": 2000,
        "custom_instruction": ""
    },
    "Analyst": {
        "model": "",
        "temperature": 0.2,
        "token_budget": 4000,
        "custom_instruction": ""
    },
    "Researcher": {
        "model": "",
        "temperature": 0.2,
        "token_budget": 4000,
        "custom_instruction": ""
    },
    "Reasoner": {
        "model": "",
        "temperature": 0.2,
        "token_budget": 3000,
        "custom_instruction": ""
    },
    "Executor": {
        "model": "",
        "temperature": 0.2,
        "token_budget": 6000,
        "custom_instruction": ""
    },
    "Verifier": {
        "model": "",
        "temperature": 0.0,
        "token_budget": 2000,
        "custom_instruction": ""
    },
    "Manager": {
        "model": "",
        "temperature": 0.1,
        "token_budget": 2000,
        "custom_instruction": ""
    },
    "MemoryAgent": {
        "model": "",
        "temperature": 0.1,
        "token_budget": 1500,
        "custom_instruction": ""
    }
}

class AgentConfigRegistry:
    def __init__(self):
        self._lock = threading.RLock()
        self._configs: Dict[str, Dict[str, Any]] = {}
        self.reset()

    def reset(self):
        with self._lock:
            self._configs = {
                k: dict(v) for k, v in DEFAULT_AGENT_CONFIGS.items()
            }

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        with self._lock:
            global_cfg = dict(self._configs.get("global", DEFAULT_AGENT_CONFIGS["global"]))
            if agent_name == "global":
                return global_cfg

            agent_cfg = self._configs.get(agent_name, {})
            merged = global_cfg.copy()
            for k, v in agent_cfg.items():
                if v is not None and v != "":
                    merged[k] = v
                elif k == "temperature" and isinstance(v, (int, float)):
                    merged[k] = float(v)
            return merged

    def get_all_configs(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "configs": {k: dict(v) for k, v in self._configs.items()},
                "available_models": AVAILABLE_MODELS,
                "presets": {
                    "deterministic": {"temperature": 0.0, "label": "Deterministic (Code / Verifier / Math)"},
                    "balanced": {"temperature": 0.2, "label": "Balanced (Structured Reasoning & Architecture)"},
                    "creative": {"temperature": 0.7, "label": "Creative (Brainstorming & Drafting)"}
                }
            }

    def update_agent_config(self, agent_name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            if agent_name not in self._configs:
                self._configs[agent_name] = self._configs.get("global", DEFAULT_AGENT_CONFIGS["global"]).copy()

            for key in ["model", "temperature", "token_budget", "custom_instruction"]:
                if key in updates:
                    val = updates[key]
                    if key == "temperature" and val is not None:
                        self._configs[agent_name]["temperature"] = max(0.0, min(1.0, float(val)))
                    elif key == "token_budget" and val is not None:
                        self._configs[agent_name]["token_budget"] = max(250, min(32000, int(val)))
                    elif key in ("model", "custom_instruction") and val is not None:
                        self._configs[agent_name][key] = str(val).strip()

            return self._configs[agent_name]

    def update_all_configs(self, bulk_updates: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        with self._lock:
            for agent_name, updates in bulk_updates.items():
                if isinstance(updates, dict):
                    self.update_agent_config(agent_name, updates)
            return self.get_all_configs()

    def get_model(self, agent_name: str) -> str:
        cfg = self.get_agent_config(agent_name)
        return cfg.get("model", "gemini-2.5-flash")

    def get_temperature(self, agent_name: str) -> float:
        cfg = self.get_agent_config(agent_name)
        return float(cfg.get("temperature", 0.2))

    def get_token_budget(self, agent_name: str, fallback: Optional[int] = None) -> int:
        cfg = self.get_agent_config(agent_name)
        configured_budget = cfg.get("token_budget")
        if configured_budget is not None and int(configured_budget) > 0:
            return int(configured_budget)
        return fallback or 3000

    def get_custom_instruction(self, agent_name: str) -> str:
        cfg = self.get_agent_config(agent_name)
        return cfg.get("custom_instruction", "").strip()

# Global singleton
agent_config_registry = AgentConfigRegistry()
