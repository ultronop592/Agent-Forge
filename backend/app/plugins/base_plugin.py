from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseWorkflowPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """The display name of the plugin workflow."""
        pass

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """Unique key name used internally."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief summary of what this workflow solves."""
        pass

    @abstractmethod
    def get_custom_system_instruction(self, agent_name: str) -> str:
        """Provides custom prompt guidelines for agents inside this plugin."""
        pass

    @abstractmethod
    def get_default_subtasks(self, prompt: str) -> List[Dict[str, Any]]:
        """Returns standard subtasks if the Planner needs default configurations."""
        pass
