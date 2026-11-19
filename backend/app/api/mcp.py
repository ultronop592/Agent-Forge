import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.security import verify_admin_key
from backend.app.database.connection import get_db
from backend.app.database.models import MCPServer, AuditLog
from backend.app.mcp.catalog import load_catalog, build_server_from_catalog, get_catalog_entry
from backend.app.mcp.client import mcp_manager
from backend.app.mcp.security import validate_command_and_args, MCPSecurityError
from backend.app.harness.errors import ToolDenied
from backend.app.harness.harness import get_current_harness

logger = logging.getLogger("agentforge.api.mcp")
router = APIRouter(prefix="/mcp", tags=["mcp"])


class MCPServerEnablePayload(BaseModel):
    catalog_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = {}
    name: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None


class ToolCallPayload(BaseModel):
    server_name: str
    tool_name: str
    arguments: Dict[str, Any]


def record_audit_log(
    db: Session,
    action: str,
    target_id: str,
    actor: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    try:
        log_entry = AuditLog(
            action=action,
            target_id=target_id,
            actor=actor,
            details=json.dumps(details) if details else None
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}")


@router.get("/catalog")
def get_catalog() -> List[Dict[str, Any]]:
    return load_catalog()


@router.get("/servers")
def list_servers(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    servers = db.query(MCPServer).all()
    result = []
    for s in servers:
        client = mcp_manager.clients.get(s.name)
        status_str = "running" if (client and client.initialized) else "stopped"
        data = s.to_dict()
        data["status"] = status_str
        data["tools_count"] = len(client.tools) if (client and client.initialized) else 0
        result.append(data)
    return result


@router.post("/servers")
async def enable_server(
    payload: MCPServerEnablePayload,
    db: Session = Depends(get_db),
    actor_id: str = Depends(verify_admin_key)
) -> Dict[str, Any]:
    if payload.catalog_id:
        try:
            spec = build_server_from_catalog(payload.catalog_id, payload.parameters)
        except ValueError as ve:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))

        server_name = spec["name"]
        command = spec["command"]
        args = spec["args"]
        required_env = spec["required_env"]
        pinned_package = spec["pinned_package"]
    else:
        if not settings.mcp_allow_dynamic_registration:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dynamic MCP server registration is disabled. Use catalog enablement."
            )

        if not payload.name or not payload.command:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Both 'name' and 'command' are required for dynamic server registration."
            )

        server_name = payload.name
        command = payload.command
        args = payload.args or []
        required_env = []
        pinned_package = None

        try:
            allowed = [c.strip() for c in settings.mcp_allowed_commands.split(",") if c.strip()]
            validate_command_and_args(command, args, allowed_commands=allowed)
        except MCPSecurityError as se:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(se))

    existing = db.query(MCPServer).filter(MCPServer.name == server_name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Server '{server_name}' is already registered."
        )

    db_server = MCPServer(
        name=server_name,
        transport="stdio",
        command=command,
        args=json.dumps(args),
        is_active=True
    )
    db.add(db_server)
    db.commit()
    db.refresh(db_server)

    success = await mcp_manager.register_and_start(
        name=server_name,
        command=command,
        args=args,
        declared_env_keys=required_env,
        expected_pinned_package=pinned_package
    )

    record_audit_log(
        db=db,
        action="enable_server" if payload.catalog_id else "register_server",
        target_id=server_name,
        actor=actor_id,
        details={
            "catalog_id": payload.catalog_id,
            "command": command,
            "args": args,
            "success": success
        }
    )

    res = db_server.to_dict()
    res["status"] = "running" if success else "failed"
    return res


@router.delete("/servers/{server_name}")
async def remove_server(
    server_name: str,
    db: Session = Depends(get_db),
    actor_id: str = Depends(verify_admin_key)
) -> Dict[str, str]:
    db_server = db.query(MCPServer).filter(MCPServer.name == server_name).first()
    if not db_server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")

    db.delete(db_server)
    db.commit()

    client = mcp_manager.clients.pop(server_name, None)
    if client:
        await client.stop()

    record_audit_log(
        db=db,
        action="delete_server",
        target_id=server_name,
        actor=actor_id
    )

    return {"message": f"Server '{server_name}' successfully removed."}


@router.get("/tools")
def list_tools() -> List[Dict[str, Any]]:
    return mcp_manager.get_all_tools()


@router.post("/tools/call")
async def call_mcp_tool(payload: ToolCallPayload) -> Dict[str, Any]:
    harness = get_current_harness()
    if harness:
        harness.authorize("executor", payload.tool_name)
    try:
        res = await mcp_manager.call_tool(
            server_name=payload.server_name,
            tool_name=payload.tool_name,
            arguments=payload.arguments,
            agent_name="executor",
        )
        return res
    except ToolDenied:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
