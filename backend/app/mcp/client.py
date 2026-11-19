import asyncio
import json
import logging
import shutil
import uuid
from typing import Dict, List, Any, Optional

from backend.app.core.config import settings
from backend.app.harness.harness import get_current_harness
from backend.app.mcp.security import (
    validate_command_and_args,
    get_sanitized_environment,
    get_posix_preexec_fn,
    kill_process_group,
    wrap_untrusted_mcp_output,
    MCPSecurityError
)

logger = logging.getLogger("agentforge.mcp")
logger.setLevel(logging.INFO)


class SingleMCPClient:
    def __init__(
        self,
        name: str,
        command: str,
        args: List[str],
        declared_env_keys: Optional[List[str]] = None,
        expected_pinned_package: Optional[str] = None
    ) -> None:
        self.name = name
        self.command = command
        self.args = args
        self.declared_env_keys = declared_env_keys or []
        self.expected_pinned_package = expected_pinned_package
        self.process: Optional[asyncio.subprocess.Process] = None
        self.read_task: Optional[asyncio.Task] = None
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.tools: List[Dict[str, Any]] = []
        self.initialized = False

    async def start(self) -> bool:
        try:
            logger.info(f"Starting MCP server '{self.name}' via stdio: {self.command} {' '.join(self.args)}")
            
            allowed = [c.strip() for c in settings.mcp_allowed_commands.split(",") if c.strip()]
            validate_command_and_args(
                command=self.command,
                args=self.args,
                allowed_commands=allowed,
                expected_pinned_package=self.expected_pinned_package
            )
            
            safe_env = get_sanitized_environment(self.declared_env_keys)
            preexec = get_posix_preexec_fn()
            exe = shutil.which(self.command) or self.command
            
            self.process = await asyncio.create_subprocess_exec(
                exe,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=safe_env,
                preexec_fn=preexec
            )
            
            self.read_task = asyncio.create_task(self._read_loop())
            
            success = await self._handshake()
            if success:
                logger.info(f"MCP server '{self.name}' successfully initialized.")
                self.tools = await self._fetch_tools()
                self.initialized = True
                return True
            else:
                logger.error(f"MCP server '{self.name}' handshake failed.")
                await self.stop()
                return False
        except MCPSecurityError as se:
            logger.error(f"Security validation failed for MCP server '{self.name}': {se}")
            return False
        except Exception as e:
            logger.error(f"Failed to start MCP server '{self.name}': {str(e)}")
            return False

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Any:
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP process not running.")
        
        req_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params
        }
        
        future = asyncio.get_running_loop().create_future()
        self.pending_requests[req_id] = future
        
        req_bytes = (json.dumps(request) + "\n").encode("utf-8")
        self.process.stdin.write(req_bytes)
        await self.process.stdin.drain()
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self.pending_requests.pop(req_id, None)
            raise TimeoutError(f"Request {method} (id: {req_id}) timed out waiting for MCP server.")

    async def _send_notification(self, method: str, params: Dict[str, Any]) -> None:
        if not self.process or not self.process.stdin:
            return
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        req_bytes = (json.dumps(notification) + "\n").encode("utf-8")
        self.process.stdin.write(req_bytes)
        await self.process.stdin.drain()

    async def _read_loop(self) -> None:
        try:
            while self.process and self.process.stdout:
                line = await self.process.stdout.readline()
                if not line:
                    break
                
                try:
                    message = json.loads(line.decode("utf-8"))
                    msg_id = message.get("id")
                    
                    if msg_id in self.pending_requests:
                        future = self.pending_requests.pop(msg_id)
                        if "error" in message:
                            future.set_exception(Exception(message["error"].get("message", "Unknown error")))
                        else:
                            future.set_result(message.get("result"))
                    else:
                        logger.debug(f"Received JSON-RPC message without matching callback: {message}")
                except json.JSONDecodeError:
                    pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in read loop for '{self.name}': {str(e)}")

    async def _handshake(self) -> bool:
        try:
            params = {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "AgentForgeClient",
                    "version": "1.0.0"
                }
            }
            res = await self._send_request("initialize", params)
            await self._send_notification("notifications/initialized", {})
            return True
        except Exception as e:
            logger.error(f"Handshake error with '{self.name}': {str(e)}")
            return False

    async def _fetch_tools(self) -> List[Dict[str, Any]]:
        try:
            res = await self._send_request("tools/list", {})
            return res.get("tools", [])
        except Exception as e:
            logger.error(f"Failed to fetch tools from '{self.name}': {str(e)}")
            return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            params = {
                "name": name,
                "arguments": arguments
            }
            res = await self._send_request("tools/call", params)
            return wrap_untrusted_mcp_output(res)
        except Exception as e:
            logger.error(f"Failed to call tool '{name}' on '{self.name}': {str(e)}")
            return {"content": [{"type": "text", "text": f"Error calling tool {name}: {str(e)}"}], "isError": True}

    async def stop(self) -> None:
        if self.read_task:
            self.read_task.cancel()
        if self.process:
            kill_process_group(self.process)
            try:
                await asyncio.wait_for(self.process.wait(), timeout=3.0)
            except Exception:
                pass
        self.initialized = False
        logger.info(f"MCP server '{self.name}' stopped.")


class MCPManager:
    def __init__(self) -> None:
        self.clients: Dict[str, SingleMCPClient] = {}

    async def register_and_start(
        self,
        name: str,
        command: str,
        args: List[str],
        declared_env_keys: Optional[List[str]] = None,
        expected_pinned_package: Optional[str] = None
    ) -> bool:
        if name in self.clients:
            await self.clients[name].stop()
        
        client = SingleMCPClient(
            name=name,
            command=command,
            args=args,
            declared_env_keys=declared_env_keys,
            expected_pinned_package=expected_pinned_package
        )
        success = await client.start()
        if success:
            self.clients[name] = client
            return True
        return False

    async def stop_all(self) -> None:
        for client in list(self.clients.values()):
            await client.stop()
        self.clients.clear()

    def get_all_tools(self) -> List[Dict[str, Any]]:
        all_tools = []
        for client_name, client in self.clients.items():
            if client.initialized:
                for tool in client.tools:
                    enriched_tool = tool.copy()
                    enriched_tool["mcp_server_name"] = client_name
                    all_tools.append(enriched_tool)
        return all_tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any], agent_name: str = "executor") -> Dict[str, Any]:
        harness = get_current_harness()
        if harness:
            harness.authorize(agent_name, tool_name)
        if server_name not in self.clients:
            return {"content": [{"type": "text", "text": f"MCP server '{server_name}' not registered."}], "isError": True}
        res = await self.clients[server_name].call_tool(tool_name, arguments)
        return wrap_untrusted_mcp_output(res)


mcp_manager = MCPManager()
