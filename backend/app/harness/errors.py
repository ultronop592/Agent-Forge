class BudgetExceeded(Exception):
    def __init__(self, reason_code: str, message: str = "") -> None:
        self.reason_code: str = reason_code
        super().__init__(message or f"Budget exceeded: {reason_code}")


class ToolDenied(Exception):
    def __init__(self, agent_name: str, tool_name: str, message: str = "") -> None:
        self.agent_name: str = agent_name
        self.tool_name: str = tool_name
        super().__init__(message or f"Tool '{tool_name}' is not permitted for agent '{agent_name}'")
