import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.app.database.connection import get_db
from backend.app.database.models import MCPServer
from backend.app.mcp.client import mcp_manager

router = APIRouter(prefix="/mcp", tags=["mcp"])

class MCPServerCreate(BaseModel):
    name: str
    command: str
    args: Optional[List[str]] = []

class ToolCallPayload(BaseModel):
    server_name: str
    tool_name: str
    arguments: Dict[str, Any]

@router.get("/servers")
def list_servers(db: Session = Depends(get_db)):
    servers = db.query(MCPServer).all()
    
    # Check current runtime client state
    result = []
    for s in servers:
        client = mcp_manager.clients.get(s.name)
        status = "running" if (client and client.initialized) else "stopped"
        data = s.to_dict()
        data["status"] = status
        data["tools_count"] = len(client.tools) if (client and client.initialized) else 0
        result.append(data)
    return result

@router.post("/servers")
async def add_server(payload: MCPServerCreate, db: Session = Depends(get_db)):
    existing = db.query(MCPServer).filter(MCPServer.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Server '{payload.name}' already registered.")
        
    args_json = json.dumps(payload.args)
    db_server = MCPServer(
        name=payload.name,
        transport="stdio",
        command=payload.command,
        args=args_json,
        is_active=True
    )
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    
    # Attempt to start in runtime client manager
    success = await mcp_manager.register_and_start(
        name=payload.name,
        command=payload.command,
        args=payload.args
    )
    
    res = db_server.to_dict()
    res["status"] = "running" if success else "failed"
    return res

@router.delete("/servers/{server_name}")
async def remove_server(server_name: str, db: Session = Depends(get_db)):
    db_server = db.query(MCPServer).filter(MCPServer.name == server_name).first()
    if not db_server:
        raise HTTPException(status_code=404, detail="Server not found")
        
    db.delete(db_server)
    db.commit()
    
    # Shut down subprocess
    client = mcp_manager.clients.pop(server_name, None)
    if client:
        await client.stop()
        
    return {"message": f"Server '{server_name}' successfully removed."}

@router.get("/tools")
def list_tools():
    # Returns all tools dynamically exposed by connected MCP servers
    return mcp_manager.get_all_tools()

@router.post("/tools/call")
async def call_mcp_tool(payload: ToolCallPayload):
    try:
        # Route execution to correct sub-client
        res = await mcp_manager.call_tool(
            server_name=payload.server_name,
            tool_name=payload.tool_name,
            arguments=payload.arguments
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
