import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    tavily_api_key: str = Field(default="", validation_alias="TAVILY_API_KEY")
    database_url: str = Field(default="sqlite:///./agentforge.db", validation_alias="DATABASE_URL")
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    mcp_servers_json: str = Field(default="[]", validation_alias="MCP_SERVERS_JSON")
    api_secret_key: str = Field(default="", validation_alias="API_SECRET_KEY")
    admin_api_key: str = Field(default="", validation_alias="ADMIN_API_KEY")
    hitl_timeout_seconds: float = Field(default=60.0, validation_alias="HITL_TIMEOUT_SECONDS")
    
    # MCP Security Settings
    mcp_allowed_commands: str = Field(default="npx,node,python", validation_alias="MCP_ALLOWED_COMMANDS")
    mcp_allow_dynamic_registration: bool = Field(default=False, validation_alias="MCP_ALLOW_DYNAMIC_REGISTRATION")
    mcp_allowed_sse_hosts: str = Field(default="", validation_alias="MCP_ALLOWED_SSE_HOSTS")
    
    # SSE Streaming & Concurrency Settings
    sse_db_pool_limit: int = Field(default=5, validation_alias="SSE_DB_POOL_LIMIT")

    # Cost Telemetry & Model Settings
    cost_model: str = Field(default="gemini-2.5-flash", validation_alias="COST_MODEL")

    harness_max_steps: int = Field(default=25, validation_alias="HARNESS_MAX_STEPS")
    harness_max_seconds: float = Field(default=300.0, validation_alias="HARNESS_MAX_SECONDS")
    harness_max_cost_usd: float = Field(default=0.50, validation_alias="HARNESS_MAX_COST_USD")
    harness_max_tokens: int = Field(default=120000, validation_alias="HARNESS_MAX_TOKENS")

    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    allowed_origins: str = Field(default="http://localhost:3000", validation_alias="ALLOWED_ORIGINS")

    # Rate Limiting Settings (Phase 3)
    rate_limit_enabled: bool = Field(default=True, validation_alias="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, validation_alias="RATE_LIMIT_PER_MINUTE")

    # LangSmith Observability & Tracing Settings
    langsmith_tracing: bool = Field(default=False, validation_alias="LANGSMITH_TRACING")
    langsmith_api_key: str = Field(default="", validation_alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="AgentForge", validation_alias="LANGSMITH_PROJECT")
    langsmith_endpoint: str = Field(default="https://api.smith.langchain.com", validation_alias="LANGSMITH_ENDPOINT")

settings = Settings()


