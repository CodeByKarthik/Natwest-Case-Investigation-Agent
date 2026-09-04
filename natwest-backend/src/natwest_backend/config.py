from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    mcp_host: str = Field(validation_alias="MCP_HOST")
    mcp_port: int = Field(validation_alias="MCP_PORT")
    api_host: str = Field(validation_alias="API_HOST")
    api_port: int = Field(validation_alias="API_PORT")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", validation_alias="LLM_MODEL")
    langsmith_tracing: str = Field(validation_alias="LANGSMITH_TRACING")
    langsmith_api_key: str = Field(validation_alias="LANGSMITH_API_KEY")
    langsmith_endpoint: str = Field(validation_alias="LANGSMITH_ENDPOINT")
    langsmith_project: str = Field(validation_alias="LANGSMITH_PROJECT")
    app_version: str = Field(validation_alias="APP_VERSION")
    redis_url: str = Field(validation_alias="REDIS_URL")

    azure_openai_api_key: str = Field(default="", validation_alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: str = Field(default="", validation_alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment: str = Field(default="", validation_alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field(default="2024-12-01-preview", validation_alias="AZURE_OPENAI_API_VERSION")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # type: ignore[call-arg]
