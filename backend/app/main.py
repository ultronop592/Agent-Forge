import os  # database reload trigger
import json
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.app.core.config import settings
from backend.app.database.connection import engine, Base, SessionLocal
from backend.app.database.models import MCPServer
from backend.app.mcp.client import mcp_manager
from backend.app.api import tasks, agents, memory, plugins, mcp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("agentforge.main")

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

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include Routers
app.include_router(tasks.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(plugins.router, prefix="/api")
app.include_router(mcp.router, prefix="/api")

@app.get("/health")
def healthcheck():
    return {"status": "healthy", "database": "connected"}

@app.on_event("startup")
async def startup_event():
    logger.info("AgentForge application startup initiated.")
    
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
    import asyncio
    # Await runtime client stops
    await mcp_manager.stop_all()
    logger.info("All MCP subprocesses stopped. Shutdown complete.")

if __name__ == "__main__":
    import asyncio
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
