# Igloo MCP Server

An MCP (Model Context Protocol) server that provides AI assistants with search capabilities for [Igloo](https://www.igloosoftware.com/) digital workplace instances.

## Features

- Full-text search across Igloo communities
- Filter by application types, date ranges, archived content, and parent paths
- Sort results by views or relevance
- Customizable server identity

## Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Access to an Igloo instance with API credentials

## Installation & Usage

### Quick Start (Direct Execution)

Run directly from GitHub without cloning:

```bash
uvx --from git+https://github.com/redhat-community-ai-tools/igloo-mcp igloo-mcp
```

Configure using environment variables (see [Configuration](#configuration) below).

### Local Development

Clone and install for local development:

```bash
git clone https://github.com/redhat-community-ai-tools/igloo-mcp.git
cd igloo-mcp
uv sync  # Creates .venv/ and installs dependencies
igloo-mcp
```

## Configuration

The server can be configured using:
- **Environment variables** (recommended for credentials): `IGLOO_MCP_*` prefix
- **CLI arguments**: kebab-case options (e.g., `--server-name`)
- **`.env` file**: for local development

### Example Configuration

Create a `.env` file in the project root:

```env
# Required
IGLOO_MCP_COMMUNITY="https://your-igloo-instance.com"
IGLOO_MCP_COMMUNITY_KEY="10"
IGLOO_MCP_APP_ID="your-app-id"
IGLOO_MCP_APP_PASS="your-app-password"
IGLOO_MCP_USERNAME="your-username"
IGLOO_MCP_PASSWORD="your-password"

# Optional
IGLOO_MCP_SERVER_NAME="Your Organization Name"
IGLOO_MCP_LOG_LEVEL="INFO"
IGLOO_MCP_TRANSPORT="stdio"
IGLOO_MCP_PAGE_SIZE=50
IGLOO_MCP_DEFAULT_LIMIT=20
```

### Configuration Parameters

**Required:**
- `IGLOO_MCP_COMMUNITY` - Base URL of your Igloo community
- `IGLOO_MCP_COMMUNITY_KEY` - Numeric identifier for your digital workplace
- `IGLOO_MCP_APP_ID` - Application ID for the Igloo API
- `IGLOO_MCP_APP_PASS` - Application password for the Igloo API
- `IGLOO_MCP_USERNAME` - Username to authenticate with
- `IGLOO_MCP_PASSWORD` - Password to authenticate with

**Optional:**
- `IGLOO_MCP_SERVER_NAME` (default: "Igloo") - Server name shown to clients
- `IGLOO_MCP_SERVER_INSTRUCTIONS` (default: "Use this server to search and retrieve information from an Igloo instance.") - Instructions describing the server's purpose and capabilities to clients.
- `IGLOO_MCP_LOG_LEVEL` (default: "INFO") - Logging level
- `IGLOO_MCP_TRANSPORT` (default: "stdio") - Transport protocol (stdio, streamable-http)
- `IGLOO_MCP_PAGE_SIZE` (default: 50) - Results per page (10-1000)
- `IGLOO_MCP_DEFAULT_LIMIT` (default: 20) - Default max search results
- `IGLOO_MCP_PROXY` - Optional proxy URL
- `IGLOO_MCP_VERIFY_SSL` (default: true) - Verify SSL certificates

### Transport Options

By default, the server uses stdio transport. For HTTP transport, set `IGLOO_MCP_TRANSPORT="streamable-http"` - the server will be available at `http://localhost:8000/mcp`.

## Available Tools

### search

Search for content in the Igloo community with extensive filtering options.

**Key Parameters:**
- `query`: Search query text
- `applications`: Filter by type (blog, wiki, document, forum, gallery, calendar, pages, people, space, microblog)
- `sort`: Sort by "default" or "views"
- `limit`: Maximum results to return
- `updated_date_type`: Filter by date (past_hour, past_24_hours, past_week, past_month, past_year, custom_range)
- `include_archived`: Include archived content (default: false)

See the tool's schema for all available parameters.

## Development

```bash
uv run pytest                      # Run tests
uv run mcp dev igloo_mcp/main.py  # Test with MCP Inspector
```

## License

See [LICENSE](LICENSE) file for details.