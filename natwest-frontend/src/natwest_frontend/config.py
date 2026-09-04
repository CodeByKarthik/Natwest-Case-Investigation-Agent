from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    keycloak_url: str = Field(validation_alias="KEYCLOAK_URL")
    keycloak_docker_url: str = Field(validation_alias="KEYCLOAK_URL_DOCKER")
    keycloak_realm: str = Field(validation_alias="KEYCLOAK_REALM")
    keycloak_client_id: str = Field(validation_alias="KEYCLOAK_CLIENT_ID")
    keycloak_client_secret: str = Field(validation_alias="KEYCLOAK_CLIENT_SECRET")
    redirect_uri: str = Field(validation_alias="REDIRECT_URI")
    api_base_url: str = Field(validation_alias="API_BASE_URL")
    api_docker_url: str = Field(validation_alias="API_DOCKER_URL")
    streamlit_host: str = Field(validation_alias="STREAMLIT_HOST")
    streamlit_port: int = Field(validation_alias="STREAMLIT_PORT")
    keycloak_external_url: str = Field(validation_alias="KEYCLOAK_EXTERNAL_URL")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # type: ignore[call-arg]
