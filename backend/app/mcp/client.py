import asyncio
import json
import logging
import sys
import uuid
from typing import Dict, List, Any, Optional

logger = logging.getLogger("agentforge.mcp")
logger.setLevel(logging.INFO)

class SingleMCPClient:
    def __init__(self, name: str, command: str, args: List[str]):
        self.name = name
        self.command = command
        self.args = args
        self.process: Optional[asyncio.subprocess.Process] = None
        self.read_task: Optional[asyncio.Task] = None
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.tools: List[Dict[str, Any]] = []
        self.initialized = False

    async def start(self) -> bool:
        try:
            logger.info(f"Starting MCP server '{self.name}' via stdio: {self.command} {' '.join(self.args)}")
            
            # Use Shell execution for windows compatibility with npx/python
            cmd_str = f"{self.command} {' '.join(self.args)}"
            self.process = await asyncio.create_subprocess_shell(
                cmd_str,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.read_task = asyncio.create_task(self._read_loop())
            
            # Handshake
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
            # Set a 30s timeout on response
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

    async def _read_loop(self):
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
                        # Log notifications or unhandled responses
                        logger.debug(f"Received JSON-RPC message without matching callback: {message}")
                except json.JSONDecodeError:
                    # Ignore corrupted stdout lines
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
            return res
        except Exception as e:
            logger.error(f"Failed to call tool '{name}' on '{self.name}': {str(e)}")
            return {"content": [{"type": "text", "text": f"Error calling tool {name}: {str(e)}"}], "isError": True}

    async def stop(self):
        if self.read_task:
            self.read_task.cancel()
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception:
                pass
        self.initialized = False
        logger.info(f"MCP server '{self.name}' stopped.")

class MCPManager:
    def __init__(self):
        self.clients: Dict[str, SingleMCPClient] = {}

    async def register_and_start(self, name: str, command: str, args: List[str]) -> bool:
        if name in self.clients:
            await self.clients[name].stop()
        
        client = SingleMCPClient(name, command, args)
        success = await client.start()
        if success:
            self.clients[name] = client
            return True
        return False

    async def stop_all(self):
        for client in list(self.clients.values()):
            await client.stop()
        self.clients.clear()

    def get_all_tools(self) -> List[Dict[str, Any]]:
        all_tools = []
        for client_name, client in self.clients.items():
            if client.initialized:
                for tool in client.tools:
                    # Enrich tool metadata with server details so we route correctly
                    enriched_tool = tool.copy()
                    enriched_tool["mcp_server_name"] = client_name
                    all_tools.append(enriched_tool)
        return all_tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if server_name not in self.clients:
            return {"content": [{"type": "text", "text": f"MCP server '{server_name}' not registered."}], "isError": True}
        return await self.clients[server_name].call_tool(tool_name, arguments)

mcp_manager = MCPManager()
