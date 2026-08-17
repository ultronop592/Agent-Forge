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
    hitl_timeout_seconds: float = Field(default=60.0, validation_alias="HITL_TIMEOUT_SECONDS")
    
    # LangSmith Observability & Tracing Settings
    langsmith_tracing: bool = Field(default=False, validation_alias="LANGSMITH_TRACING")
    langsmith_api_key: str = Field(default="", validation_alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="AgentForge", validation_alias="LANGSMITH_PROJECT")
    langsmith_endpoint: str = Field(default="https://api.smith.langchain.com", validation_alias="LANGSMITH_ENDPOINT")

settings = Settings()


