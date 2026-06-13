from __future__ import annotations

from importlib import metadata
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

from buddy.utils.log import logger

BUDDY_CLI_CONFIG_DIR: Path = Path.home().resolve().joinpath(".config").joinpath("buddy")


def get_app_version() -> str:
    """Get the app version, handling both installed packages and local development."""
    try:
        return metadata.version("buddy")
    except metadata.PackageNotFoundError:
        # Fallback for local development when buddy is not installed as a package
        return "dev-local"


class BuddyCliSettings(BaseSettings):
    app_name: str = "buddy"
    app_version: str = get_app_version()

    tmp_token_path: Path = BUDDY_CLI_CONFIG_DIR.joinpath("tmp_token")
    config_file_path: Path = BUDDY_CLI_CONFIG_DIR.joinpath("config.json")
    credentials_path: Path = BUDDY_CLI_CONFIG_DIR.joinpath("credentials.json")
    ai_conversations_path: Path = BUDDY_CLI_CONFIG_DIR.joinpath("ai_conversations.json")
    auth_token_cookie: str = "__BUDDY_session"
    auth_token_header: str = "X-BUDDY-AUTH-TOKEN"

    api_runtime: str = "prd"
    api_enabled: bool = True
    alpha_features: bool = False
    api_url: str = Field("https://api.buddy-ai.com", validate_default=True)
    cli_auth_url: str = Field("https://app.buddy-ai.com", validate_default=True)
    signin_url: str = Field("https://app.buddy-ai.com/login", validate_default=True)
    playground_url: str = Field("https://app.buddy-ai.com/playground", validate_default=True)

    model_config = SettingsConfigDict(env_prefix="BUDDY_")

    @field_validator("api_runtime", mode="before")
    def validate_runtime_env(cls, v):
        """Validate api_runtime."""

        valid_api_runtimes = ["dev", "stg", "prd"]
        if v.lower() not in valid_api_runtimes:
            raise ValueError(f"Invalid api_runtime: {v}")

        return v.lower()

    @field_validator("cli_auth_url", mode="before")
    def update_cli_auth_url(cls, v, info: ValidationInfo):
        api_runtime = info.data["api_runtime"]
        if api_runtime == "dev":
            return "http://localhost:3000/cli-auth"
        elif api_runtime == "stg":
            return "https://app-stg.buddy.com/cli-auth"
        else:
            return "https://app.buddy.com/cli-auth"

    @field_validator("signin_url", mode="before")
    def update_signin_url(cls, v, info: ValidationInfo):
        api_runtime = info.data["api_runtime"]
        if api_runtime == "dev":
            return "http://localhost:3000/login"
        elif api_runtime == "stg":
            return "https://app-stg.buddy.com/login"
        else:
            return "https://app.buddy.com/login"

    @field_validator("playground_url", mode="before")
    def update_playground_url(cls, v, info: ValidationInfo):
        api_runtime = info.data["api_runtime"]
        if api_runtime == "dev":
            return "http://localhost:3000/playground"
        elif api_runtime == "stg":
            return "https://app-stg.buddy.com/playground"
        else:
            return "https://app.buddy.com/playground"

    @field_validator("api_url", mode="before")
    def update_api_url(cls, v, info: ValidationInfo):
        api_runtime = info.data["api_runtime"]
        if api_runtime == "dev":
            from os import getenv

            if getenv("BUDDY_RUNTIME") == "docker":
                return "http://host.docker.internal:7070"
            return "http://localhost:7070"
        elif api_runtime == "stg":
            return "https://api-stg.buddy.com"
        else:
            return "https://api.buddy.com"

    def gate_alpha_feature(self):
        if not self.alpha_features:
            logger.error("This is an Alpha feature not for general use.\nPlease message the Buddy team for access.")
            exit(1)


BUDDY_cli_settings = BuddyCliSettings()



