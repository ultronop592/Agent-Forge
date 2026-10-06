import os
import json
import asyncio
import logging
from typing import Optional, List
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.app.core.config import settings
from backend.app.core.telemetry import setup_langsmith
from backend.app.database.connection import engine, Base, SessionLocal, get_database_status
from backend.app.database.models import MCPServer
from backend.app.mcp.client import mcp_manager
from backend.app.api import tasks, agents, memory, plugins, mcp, evals, export

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("agentforge.main")

# Initialize LangSmith / LangGraph tracing environment
setup_langsmith()

# Generate Database Tables
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

# CORS configuration — reads comma-separated origins from ALLOWED_ORIGINS env var
# e.g. ALLOWED_ORIGINS=https://agentforge.vercel.app,https://localhost:3000
_raw_origins = getattr(settings, "allowed_origins", None) or os.environ.get("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]


def validate_allowed_origins(origins: list) -> Optional[str]:
    """Validate CORS ALLOWED_ORIGINS configuration and return warning message if insecure."""
    if "*" in origins:
        return (
            "⚠️ [Security Warning] ALLOWED_ORIGINS contains wildcard '*' with allow_credentials=True. "
            "In production environments, specify explicit origins (e.g. ALLOWED_ORIGINS=https://agentforge.vercel.app) "
            "to prevent Cross-Origin Resource Sharing (CORS) security vulnerabilities."
        )
    if not origins:
        return "⚠️ [Security Warning] ALLOWED_ORIGINS is empty. All cross-origin browser requests will be blocked."
    return None


from backend.app.core.rate_limiter import RateLimitMiddleware, rate_limiter

# Rate Limiting Middleware (Phase 3: 60 requests/min per IP/token)
app.add_middleware(RateLimitMiddleware, limiter=rate_limiter)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

from backend.app.core.security import verify_api_key

# Include Routers with Security Dependency
app.include_router(tasks.router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(agents.router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(memory.router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(plugins.router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(mcp.router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(evals.router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(export.router, prefix="/api", dependencies=[Depends(verify_api_key)])

@app.get("/health")
def healthcheck():
    db_status = get_database_status()
    is_ok = db_status.get("status") == "connected"
    return {
        "status": "healthy" if is_ok else "degraded",
        "database": "connected" if is_ok else "disconnected",
        "database_details": db_status
    }



@app.on_event("startup")
async def startup_event():
    logger.info("AgentForge application startup initiated.")

    # Validate ALLOWED_ORIGINS and emit warning if wildcard or empty
    cors_warning = validate_allowed_origins(ALLOWED_ORIGINS)
    if cors_warning:
        logger.warning(cors_warning)
    else:
        logger.info(f"🔒 CORS configured with {len(ALLOWED_ORIGINS)} allowed origin(s): {ALLOWED_ORIGINS}")

    if rate_limiter.enabled:
        logger.info(f"🛡️ Rate Limiting ENABLED: {rate_limiter.requests_per_minute} req/min per IP/token (Sliding Window)")
    else:
        logger.info("🛡️ Rate Limiting DISABLED")
    
    # Load and initialize registered MCP servers from database
    db = SessionLocal()
    try:
        servers = db.query(MCPServer).filter(MCPServer.is_active == True).all()
        logger.info(f"Loading {len(servers)} active MCP servers from database.")
        for server in servers:
            try:
                args = json.loads(server.args) if server.args else []
                # Start MCP process
                asyncio.create_task(mcp_manager.register_and_start(
                    name=server.name,
                    command=server.command,
                    args=args
                ))
            except Exception as ex:
                logger.error(f"Failed to schedule startup for MCP server '{server.name}': {ex}")
    except Exception as e:
        logger.error(f"Failed to load MCP configurations: {e}")
    finally:
        db.close()
        
    # Also load from environment string if provided
    if settings.mcp_servers_json and settings.mcp_servers_json != "[]":
        try:
            env_servers = json.loads(settings.mcp_servers_json)
            logger.info(f"Loading {len(env_servers)} MCP servers from environment.")
            for s in env_servers:
                asyncio.create_task(mcp_manager.register_and_start(
                    name=s.get("name"),
                    command=s.get("command"),
                    args=s.get("args", [])
                ))
        except Exception as e:
            logger.error(f"Failed to load MCP configurations from env json: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("AgentForge shutting down, stopping MCP subprocesses...")
    # Await runtime client stops
    await mcp_manager.stop_all()
    logger.info("All MCP subprocesses stopped. Shutdown complete.")

if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
