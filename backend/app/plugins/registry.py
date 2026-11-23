import logging
from typing import Dict, List, Type
from backend.app.plugins.base_plugin import BaseWorkflowPlugin

logger = logging.getLogger("agentforge.plugins")

class PluginRegistry:
    def __init__(self):
        self._plugins: Dict[str, BaseWorkflowPlugin] = {}
        self._aliases: Dict[str, str] = {
            "code_fix": "software_debugging",
            "deep_analysis": "general_analysis",
            "market_research": "startup_research",
            "fact_check_qa": "startup_research",
        }

    def register(self, plugin: BaseWorkflowPlugin):
        self._plugins[plugin.plugin_id] = plugin
        logger.info(f"Registered plugin: {plugin.name} ({plugin.plugin_id})")

    def get_plugin(self, plugin_id: str) -> BaseWorkflowPlugin:
        canonical_id = self._aliases.get(plugin_id, plugin_id)
        if canonical_id in self._plugins:
            return self._plugins[canonical_id]
        if plugin_id in self._plugins:
            return self._plugins[plugin_id]
        # Return the first one as default if invalid id
        return list(self._plugins.values())[0] if self._plugins else None

    def get_all_plugins(self) -> List[BaseWorkflowPlugin]:
        return list(self._plugins.values())

plugin_registry = PluginRegistry()

# Import plugins to register them
from backend.app.plugins.software_debug import SoftwareDebugPlugin
from backend.app.plugins.startup_research import StartupResearchPlugin
from backend.app.plugins.general_analysis import GeneralAnalysisPlugin
from backend.app.plugins.document_qa import DocumentQAPlugin
from backend.app.plugins.code_review import CodeReviewPlugin

plugin_registry.register(SoftwareDebugPlugin())
plugin_registry.register(StartupResearchPlugin())
plugin_registry.register(GeneralAnalysisPlugin())
plugin_registry.register(DocumentQAPlugin())
plugin_registry.register(CodeReviewPlugin())

