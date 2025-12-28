from typing import Literal
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """
    Configuration settings for the Igloo MCP server.

    Settings can be provided via a .env file, environment variables, or command-line arguments.
    """
    model_config = SettingsConfigDict(
        env_prefix="IGLOO_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        cli_parse_args=True,
        cli_kebab_case=True,
        case_sensitive=False,
        extra="ignore",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="The logging level for the application.",
    )

    community: str = Field(
        default=...,
        description="The base URL of the Igloo community. Example: 'https://iglooe.mysite.com'",
    )
    community_key: str = Field(
        default=...,
        description="The numeric identifier for your digital workplace. Should be a number (e.g. '10').",
    )
    app_id: str = Field(
        default=...,
        description="The application ID for the Igloo API.",
    )
    app_pass: SecretStr = Field(
        default=...,
        description="The application password for the Igloo API.",
    )
    username: str = Field(
        default=...,
        description="The username to authenticate with.",
        )
    password: SecretStr = Field(
        default=...,
        description="The password to authenticate with.",
    )
    proxy: str | None = Field(
        default=None,
        description="An optional proxy URL to use for requests.",
    )
    verify_ssl: bool = Field(
        default=True,
        description="Whether to verify SSL certificates when making requests.",
    )
    page_size: int = Field(
        default=50,
        ge=10,
        le=1000,
        description="The number of results to fetch per page for paginated results.",
    )
    default_limit: int = Field(
        default=20,
        ge=1,
        le=1000,
        description="The default maximum number of search results to return when no limit is specified.",
    )
    transport: Literal["stdio", "streamable-http"] = Field(
        default="stdio",
        description="The MCP transport protocol to use. 'stdio' for standard input/output (default), 'streamable-http' for HTTP server on port 8000.",
    )
    server_name: str = Field(
        default="Igloo",
        description="The name of the MCP server. Can be customized to match your Igloo instance name.",
    )
    server_instructions: str = Field(
        default="Use this server to search and retrieve information from an Igloo instance.",
        description="Instructions that describe the server's purpose and capabilities. These are displayed to MCP clients and can reference your custom Igloo instance name.",
    )
    fetch_max_length: int = Field(
        default=50000,
        ge=1000,
        le=500000,
        description="Maximum length of Markdown content returned by the fetch tool. Content exceeding this limit will be truncated.",
    )
    fetch_timeout: float = Field(
        default=15.0,
        ge=5.0,
        le=120.0,
        description="Timeout in seconds for fetch requests.",
    )
    fetch_max_pages: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of pages that can be fetched in a single multi-URL request.",
    )
