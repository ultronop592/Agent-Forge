from typing import Dict, List, Optional
from backend.app.plugins.base_plugin import BaseWorkflowPlugin

DEFAULT_ALLOWLIST: Dict[str, List[str]] = {
    "planner": [],
    "analyst": ["tavily_search"],
    "memory_agent": ["memory_search"],
    "memory": ["memory_search"],
    "executor": [],
    "verifier": [],
}


def get_default_tool_permissions(agent_name: str) -> List[str]:
    return list(DEFAULT_ALLOWLIST.get(agent_name.lower(), []))


def build_tool_allowlist(plugin: Optional[BaseWorkflowPlugin] = None) -> Dict[str, List[str]]:
    allowlist: Dict[str, List[str]] = {
        k: list(v) for k, v in DEFAULT_ALLOWLIST.items()
    }
    if plugin:
        for agent in list(allowlist.keys()):
            extra = plugin.get_tool_permissions(agent)
            if extra:
                allowlist[agent] = list(set(allowlist[agent] + extra))
    return allowlist
