from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from typing import AsyncIterator, Literal
 
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
 
from igloo_mcp.config import Config
from igloo_mcp.formatter import format_search_results
from igloo_mcp.igloo import ApplicationType, IglooClient, UpdatedDateType
from igloo_mcp.logger import logger, configure_logger
from igloo_mcp.sorting import SortType, sort_results


@dataclass
class AppContext:
    """Application context that's shared across all tools."""
    igloo_client: IglooClient
    config: Config


_config = Config()

@asynccontextmanager
async def lifespan(mcp: FastMCP) -> AsyncIterator[AppContext]:
    """
    Asynchronous context manager for the lifespan of the MCP server.

    This function initializes and authenticates the Igloo client on startup
    and yields it to the application state.
    """
    configure_logger(log_level=_config.log_level)

    client = IglooClient(
        community=_config.community,
        community_key=_config.community_key,
        app_id=_config.app_id,
        app_pass=_config.app_pass.get_secret_value(),
        username=_config.username,
        password=_config.password.get_secret_value(),
        proxy=_config.proxy,
        verify_ssl=_config.verify_ssl,
        page_size=_config.page_size,
    )

    try:
        await client.authenticate()
        logger.info(f"Successfully authenticated with Igloo community: {_config.community}")
        yield AppContext(igloo_client=client, config=_config)
 
    except Exception:
        logger.exception("Failed to authenticate with Igloo on startup")
        raise
 
    finally:
        await client._client.aclose()
        logger.info("Igloo client connection closed.")


mcp = FastMCP(
    name=_config.server_name,
    instructions=_config.server_instructions,
    lifespan=lifespan,
)


@mcp.tool(name="search")
async def search_tool(
    query: str | None = None,
    applications: list[Literal["blog", "wiki", "document", "forum", "gallery", "calendar", "pages", "people", "space", "microblog"]] | None = None,
    parent_href: str | None = None,
    search_all: bool = True,
    include_microblog: bool = True,
    include_archived: bool = False,
    updated_date_type: Literal["past_hour", "past_24_hours", "past_week", "past_month", "past_year", "custom_range"] | None = None,
    updated_date_range_from: date | None = None,
    updated_date_range_to: date | None = None,
    pagination_page_size: int | None = None,
    sort: SortType = "default",
    limit: int | None = None,
    ctx: Context[ServerSession, AppContext] = None,
) -> str:
    """
    Search for content in the Igloo community.

    Args:
        query (str, optional): Search query. Supports advanced operators for precise matching.
            Use keywords, not sentences ("employee benefits" not "show me employee benefits"). Queries are case-insensitive.
            Operators: `"<text>"` for exact phrase, `|` for OR, `+-` to exclude, `*` for wildcard suffix
        applications (list[str], optional): Filter by content types (OR logic).
            Options: "blog", "wiki", "document", "forum", "gallery", "calendar", "pages", "people", "space", "microblog".
        parent_href (str, optional): Limit search to a specific space/location path.
        search_all (bool, optional): True = ALL keywords must match (AND), False = ANY keyword matches (OR). Default: True.
        include_microblog (bool, optional): Include microblog posts in results. Default: True.
        include_archived (bool, optional): Include archived content in results. Default: False.
        updated_date_type (str, optional): Filter by last update time.
            Options: "past_hour", "past_24_hours", "past_week", "past_month", "past_year", "custom_range".
        updated_date_range_from (date, optional): Start date for custom range (required if updated_date_type="custom_range").
        updated_date_range_to (date, optional): End date for custom range (required if updated_date_type="custom_range").
        pagination_page_size (int, optional): Results per page. Overrides default page_size if provided.
        sort (SortType, optional): Sorting method. "default" = relevance-based, "views" = most viewed first. Default: "default".
        limit (int, optional): Maximum results to return. Uses configured default_limit if not specified.

    Returns:
        str: Formatted search results optimized for LLM readability with metadata and content snippets.

    Notes:
        - Stop words (a, an, the, is, etc.) are automatically ignored
        - When using non-default sort, all results are fetched first, then sorted and limited
    """
    formatted_applications = None
    if applications:
        formatted_applications = [ApplicationType[app_type.upper()] for app_type in applications]

    formatted_updated_date_type = None
    if updated_date_type:
        formatted_updated_date_type = UpdatedDateType[updated_date_type.upper()]

    client = ctx.request_context.lifespan_context.igloo_client
    config = ctx.request_context.lifespan_context.config

    effective_limit = limit if limit is not None else config.default_limit
    limit_for_search = effective_limit if sort == "default" else None

    raw_results = await client.search(
        query=query,
        applications=formatted_applications,
        parent_href=parent_href,
        search_all=search_all,
        include_microblog=include_microblog,
        include_archived=include_archived,
        updated_date_type=formatted_updated_date_type,
        updated_date_range_from=updated_date_range_from,
        updated_date_range_to=updated_date_range_to,
        pagination_page_size=pagination_page_size,
        limit=limit_for_search,
    )

    fields_mapping = {
        "id": "id",
        "title": "title",
        "applicationType": "type",
        "href": "relative_url",
        "content": "content",
        "description": "description",
        "modifiedDate": "modified_date",
        "numberOfComments": "comments_count",
        "numberOfViews": "views_count",
        "numberOfLikes": "likes_count",
        "isArchived": "is_archived",
        "isRecommended": "is_recommended",
        "labels": "labels",
    }

    output_results = [
        {
            **{fields_mapping[key]: value for key, value in item.items() if key in fields_mapping},
            "full_url": f"{config.community}{item['href']}"
        }
        for item in raw_results
    ]

    sorted_results = sort_results(results=output_results, sort_by=sort)

    sorted_results = sorted_results[:effective_limit]

    search_params = {
        "query": query,
        "applications": applications,
        "parent_href": parent_href,
        "updated_date_type": updated_date_type,
        "updated_date_range_from": updated_date_range_from,
        "updated_date_range_to": updated_date_range_to,
        "sort": sort,
        "limit": effective_limit,
    }

    total_found = len(raw_results)

    return format_search_results(
        results=sorted_results,
        search_params=search_params,
        total_found=total_found,
    )


def main():
    """Main entry point for the MCP server."""
    try:
        mcp.run(transport=_config.transport)

    except Exception as e:
        logger.exception(f"Failed to start MCP server: {e}")
        raise


if __name__ == "__main__":
    main()