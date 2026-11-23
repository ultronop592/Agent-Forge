import os
import json
import asyncio
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.app.core.config import settings
from backend.app.core.telemetry import setup_langsmith
from backend.app.database.connection import engine, Base, SessionLocal, get_database_status
from backend.app.database.models import MCPServer
from backend.app.database.memory_search import verify_postgres_memory_schema
from backend.app.workflows.heartbeat import reap_zombies, reaper_background_loop, handle_graceful_shutdown
from backend.app.mcp.client import mcp_manager
from backend.app.mcp.catalog import load_catalog
from backend.app.mcp.security import validate_command_and_args, MCPSecurityError
from backend.app.api import tasks, agents, memory, plugins, mcp, evals, export

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("agentforge.main")

setup_langsmith()

try:
    logger.info("Initializing database and building tables...")
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logger.error(f"Database table generation failed: {e}")

app = FastAPI(
    title="AgentForge Core API",
    description="Multi-Agent Collaborative Workforce Orchestrator Backend",
    version="1.0.0"
)

_raw_origins = getattr(settings, "allowed_origins", None) or os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]


def validate_production_environment(
    environment: Optional[str] = None,
    api_secret_key: Optional[str] = None,
    admin_api_key: Optional[str] = None,
    allowed_origins: Optional[List[str]] = None
) -> None:
    env = (environment if environment is not None else getattr(settings, "environment", None) or os.environ.get("ENVIRONMENT", "development")).strip().lower()
    if env == "production":
        admin_key = admin_api_key if admin_api_key is not None else (getattr(settings, "admin_api_key", "") or os.environ.get("ADMIN_API_KEY", ""))
        if not admin_key or not admin_key.strip():
            raise RuntimeError(
                "Refusing to start in production environment: ADMIN_API_KEY is empty. "
                "Set ADMIN_API_KEY in your environment or Render dashboard."
            )

        origins = allowed_origins if allowed_origins is not None else ALLOWED_ORIGINS
        if not origins or "*" in origins:
            raise RuntimeError(
                "Refusing to start in production environment: ALLOWED_ORIGINS cannot be empty or contain wildcard '*'."
            )


def validate_allowed_origins(origins: List[str], environment: Optional[str] = None) -> Optional[str]:
    env = (environment or getattr(settings, "environment", None) or os.environ.get("ENVIRONMENT", "development")).strip().lower()
    if env == "production":
        if not origins or "*" in origins:
            raise RuntimeError(
                "Refusing to start in production environment: ALLOWED_ORIGINS cannot be empty or contain wildcard '*'."
            )
    if "*" in origins:
        return (
            "[Security Warning] ALLOWED_ORIGINS contains wildcard '*' with allow_credentials=True. "
            "In production environments, specify explicit origins (e.g. ALLOWED_ORIGINS=https://agentforge.vercel.app) "
            "to prevent Cross-Origin Resource Sharing (CORS) security vulnerabilities."
        )
    if not origins:
        return "[Security Warning] ALLOWED_ORIGINS is empty. All cross-origin browser requests will be blocked."
    return None


validate_production_environment()

from backend.app.core.rate_limiter import RateLimitMiddleware, rate_limiter

app.add_middleware(RateLimitMiddleware, limiter=rate_limiter)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

from backend.app.core.security import verify_api_key

app.include_router(tasks.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(plugins.router, prefix="/api")
app.include_router(mcp.router, prefix="/api")
app.include_router(evals.router, prefix="/api")
app.include_router(export.router, prefix="/api")


@app.get("/health")
def healthcheck() -> Dict[str, Any]:
    db_status = get_database_status()
    is_ok = db_status.get("status") == "connected"
    return {
        "status": "healthy" if is_ok else "degraded",
        "database": "connected" if is_ok else "disconnected",
        "database_details": db_status
    }


def validate_mcp_entry(name: str, command: str, args: List[str]) -> bool:
    catalog = load_catalog()
    catalog_match = None
    for entry in catalog:
        if entry.get("name") == name or entry.get("id") == name:
            catalog_match = entry
            break

    expected_pinned = catalog_match.get("pinned_package") if catalog_match else None
    allowed = [c.strip() for c in settings.mcp_allowed_commands.split(",") if c.strip()]
    try:
        validate_command_and_args(
            command=command,
            args=args,
            allowed_commands=allowed,
            expected_pinned_package=expected_pinned
        )
        return True
    except MCPSecurityError as e:
        logger.warning(f"MCP server entry '{name}' failed security validation: {e}")
        return False


_reaper_task: Optional[asyncio.Task] = None


@app.on_event("startup")
async def startup_event() -> None:
    global _reaper_task
    logger.info("AgentForge application startup initiated.")

    validate_production_environment()

    cors_warning = validate_allowed_origins(ALLOWED_ORIGINS)
    if cors_warning:
        logger.warning(cors_warning)
    else:
        logger.info(f"CORS configured with {len(ALLOWED_ORIGINS)} allowed origin(s): {ALLOWED_ORIGINS}")

    if rate_limiter.enabled:
        logger.info(f"Rate Limiting ENABLED: {rate_limiter.requests_per_minute} req/min per IP/token (Sliding Window)")
    else:
        logger.info("Rate Limiting DISABLED")
    
    db = SessionLocal()
    try:
        verify_postgres_memory_schema(db)
        reap_zombies(db, getattr(settings, "task_stale_seconds", 120))
        servers = db.query(MCPServer).filter(MCPServer.is_active == True).all()
        logger.info(f"Validating and loading {len(servers)} active MCP servers from database.")
        for server in servers:
            try:
                args = json.loads(server.args) if server.args else []
                is_valid = validate_mcp_entry(server.name, server.command, args)
                if not is_valid:
                    logger.warning(f"Deactivating invalid MCP server '{server.name}' in database.")
                    server.is_active = False
                    db.commit()
                    continue

                asyncio.create_task(mcp_manager.register_and_start(
                    name=server.name,
                    command=server.command,
                    args=args
                ))
            except Exception as ex:
                logger.error(f"Failed to schedule startup for MCP server '{server.name}': {ex}")
    except Exception as e:
        logger.error(f"Failed to load MCP configurations from database: {e}")
    finally:
        db.close()
        
    if settings.mcp_servers_json and settings.mcp_servers_json != "[]":
        try:
            env_servers = json.loads(settings.mcp_servers_json)
            logger.info(f"Validating and loading {len(env_servers)} MCP servers from environment.")
            for s in env_servers:
                name = s.get("name", "")
                command = s.get("command", "")
                args = s.get("args", [])
                if not validate_mcp_entry(name, command, args):
                    logger.warning(f"Skipping invalid MCP server '{name}' from MCP_SERVERS_JSON.")
                    continue

                asyncio.create_task(mcp_manager.register_and_start(
                    name=name,
                    command=command,
                    args=args
                ))
        except Exception as e:
            logger.error(f"Failed to load MCP configurations from env json: {e}")

    _reaper_task = asyncio.create_task(reaper_background_loop())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("AgentForge shutting down, stopping background tasks and MCP subprocesses...")
    global _reaper_task
    if _reaper_task and not _reaper_task.done():
        _reaper_task.cancel()

    db = SessionLocal()
    try:
        handle_graceful_shutdown(db)
    except Exception as ex:
        logger.warning(f"Error during graceful shutdown handling: {ex}")
    finally:
        db.close()

    await mcp_manager.stop_all()
    logger.info("All background tasks and MCP subprocesses stopped. Shutdown complete.")


if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
