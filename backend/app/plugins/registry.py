import logging
from typing import Dict, List, Type
from backend.app.plugins.base_plugin import BaseWorkflowPlugin

logger = logging.getLogger("agentforge.plugins")

class PluginRegistry:
    def __init__(self):
        self._plugins: Dict[str, BaseWorkflowPlugin] = {}

    def register(self, plugin: BaseWorkflowPlugin):
        self._plugins[plugin.plugin_id] = plugin
        logger.info(f"Registered plugin: {plugin.name} ({plugin.plugin_id})")

    def get_plugin(self, plugin_id: str) -> BaseWorkflowPlugin:
        if plugin_id not in self._plugins:
            # Return the first one as default if invalid id
            return list(self._plugins.values())[0] if self._plugins else None
        return self._plugins[plugin_id]

    def get_all_plugins(self) -> List[BaseWorkflowPlugin]:
        return list(self._plugins.values())

plugin_registry = PluginRegistry()

# Import plugins to register them
from backend.app.plugins.software_debug import SoftwareDebugPlugin
from backend.app.plugins.startup_research import StartupResearchPlugin

plugin_registry.register(SoftwareDebugPlugin())
plugin_registry.register(StartupResearchPlugin())
