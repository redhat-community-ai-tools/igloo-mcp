from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from typing import AsyncIterator, Literal

import httpx
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from igloo_mcp.config import Config
from igloo_mcp.converter import convert_html_to_markdown, OffsetError, SectionNotFoundError, extract_section
from igloo_mcp.formatter import format_search_results, format_fetch_result, format_fetch_results, format_truncation_metadata
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
    ctx: Context[ServerSession, AppContext],
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


@mcp.tool(name="fetch")
async def fetch_tool(
    ctx: Context[ServerSession, AppContext],
    url: str | list[str],
    max_length: int | None = None,
    start_index: int | None = None,
    section: str | None = None,
) -> str:
    """
    Fetch one or more pages from the Igloo community and convert to Markdown.

    Retrieves the HTML content of the specified URL(s) and converts it to clean
    Markdown for LLM consumption. All URLs must belong to the configured
    Igloo community.

    Args:
        url: A single URL or list of URLs to fetch.
            All URLs must be from the configured Igloo community.
            Example single: "https://igloo.mysite.com/wiki/article-title"
            Example multiple: ["https://igloo.mysite.com/wiki/page1", "https://igloo.mysite.com/wiki/page2"]
        max_length: Maximum length of the returned Markdown content per page.
            If exceeded, content is truncated with an indicator.
            Uses configured default if not specified.
        start_index: Character offset to start reading from (for continuation).
            Used with the cursor from a previous truncated response's CONTINUE instruction.
            The server provides `next_start_index` in truncated responses - copy that value here.
            Ignored when url is a list (multi-URL batch mode).
            Example: If previous response showed "CONTINUE: fetch(url=..., start_index=49801)",
            use start_index=49801 to continue reading.
        section: Name of section to jump to (e.g., "API Reference", "Configuration").
            Matches Markdown headers. Case-insensitive. Leading '#' characters are stripped.
            Cannot be used with start_index.
            Ignored when url is a list (multi-URL mode).
            When section is found, returns that section's content (max_length applies to section).
            If section is not found, returns an error with available section names.

    Returns:
        str: Formatted output containing page title, URL, and Markdown content.
            For multiple URLs, pages are separated with clear headers.
            When content is truncated, includes instructions to continue reading with start_index.

    Notes:
        - Only URLs from the configured community are allowed
        - Navigation, scripts, ads, and other non-content elements are removed
        - Use this tool to get the full content of pages found via search
        - Multiple URLs are fetched concurrently for efficiency
        - Maximum number of URLs per request is limited by fetch_max_pages config
        - For large documents, follow CONTINUE instructions to read remaining content
        - Use section parameter to jump directly to a specific heading in the document
    """
    client = ctx.request_context.lifespan_context.igloo_client
    config = ctx.request_context.lifespan_context.config

    effective_max_length = max_length if max_length is not None else config.fetch_max_length

    # Handle single URL case (supports start_index and section for navigation)
    if isinstance(url, str):
        # Mutual exclusion: section and start_index cannot be used together
        if section is not None and start_index is not None:
            return "Error: Cannot use both 'section' and 'start_index' parameters. Use 'section' to jump to a named section, or 'start_index' for offset-based continuation."
        
        try:
            html_content = await client.fetch_page(url)
        except ValueError as e:
            return f"Error: {e}"
        except httpx.HTTPStatusError as e:
            return f"Error: HTTP {e.response.status_code} - Failed to fetch page"
        except httpx.TimeoutException:
            return f"Error: Request timed out while fetching {url}"

        # If section is specified, extract that section first
        if section is not None:
            # First convert to markdown without truncation to extract section
            full_conversion = convert_html_to_markdown(
                html_string=html_content,
                max_length=None,  # No truncation yet
            )
            
            try:
                section_content, section_offset = extract_section(
                    full_conversion.content, section
                )
            except SectionNotFoundError as e:
                return f"Error: {e}"
            
            # Now apply max_length truncation to the extracted section
            # We use the section content directly, treating it as standalone content
            from igloo_mcp.converter import (
                find_smart_truncation_point,
                balance_code_fences,
                extract_section_headers,
                _get_current_section_path,
                _get_remaining_sections,
                TruncationMetadata,
                ConversionResult,
            )
            
            section_length = len(section_content)
            if effective_max_length is not None and section_length > effective_max_length:
                # Apply smart truncation to section content
                headers = extract_section_headers(section_content)
                truncation_point = find_smart_truncation_point(
                    section_content, effective_max_length
                )
                truncated = section_content[:truncation_point]
                truncated = balance_code_fences(truncated)
                
                # Build metadata - next_start_index is absolute in original document
                next_absolute_index = section_offset + truncation_point
                metadata = TruncationMetadata(
                    status="partial",
                    chars_returned=len(truncated),
                    chars_total=len(full_conversion.content),
                    next_start_index=next_absolute_index,
                    current_path=_get_current_section_path(headers, truncation_point),
                    remaining_sections=_get_remaining_sections(headers, truncation_point),
                )
                conversion_result = ConversionResult(content=truncated, metadata=metadata)
            else:
                # Section fits within max_length
                metadata = TruncationMetadata(
                    status="complete",
                    chars_returned=section_length,
                    chars_total=len(full_conversion.content),
                    next_start_index=None,
                    current_path=None,
                    remaining_sections=[],
                )
                conversion_result = ConversionResult(content=section_content, metadata=metadata)
            
            # Build output for section mode
            output = format_fetch_result(
                url=url,
                markdown=conversion_result.content,
                start_index=None,
            )
            
            if conversion_result.metadata is not None:
                output += format_truncation_metadata(conversion_result.metadata, url)
            
            return output

        # Standard path: no section specified
        try:
            conversion_result = convert_html_to_markdown(
                html_string=html_content,
                max_length=effective_max_length,
                start_index=start_index,
            )
        except OffsetError as e:
            return f"Error: {e}"

        # Build output with optional truncation metadata
        output = format_fetch_result(
            url=url,
            markdown=conversion_result.content,
            start_index=start_index,
        )
        
        # Append truncation metadata if content was truncated or if reading from offset
        if conversion_result.metadata is not None:
            output += format_truncation_metadata(conversion_result.metadata, url)
        
        return output

    # Handle multiple URLs case
    urls = url  # Rename for clarity

    # Check max pages limit
    if len(urls) > config.fetch_max_pages:
        return f"Error: Too many URLs requested ({len(urls)}). Maximum allowed is {config.fetch_max_pages}."

    if len(urls) == 0:
        return "Error: No URLs provided."

    # Fetch all pages concurrently
    fetch_results = await client.fetch_pages(urls)

    # Convert HTML to Markdown for each successful fetch
    formatted_results = []
    for page_url, result in zip(urls, fetch_results):
        if isinstance(result, Exception):
            # Format error message based on exception type
            if isinstance(result, ValueError):
                error_msg = str(result)
            elif isinstance(result, httpx.HTTPStatusError):
                error_msg = f"HTTP {result.response.status_code} - Failed to fetch page"
            elif isinstance(result, httpx.TimeoutException):
                error_msg = f"Request timed out while fetching {page_url}"
            else:
                error_msg = f"Unexpected error: {result}"
            formatted_results.append({
                "url": page_url,
                "error": error_msg,
            })
        else:
            conversion_result = convert_html_to_markdown(
                html_string=result,
                max_length=effective_max_length,
            )
            
            # Build markdown with optional truncation metadata
            markdown_output = conversion_result.content
            if conversion_result.metadata is not None:
                markdown_output += format_truncation_metadata(conversion_result.metadata, page_url)
            
            formatted_results.append({
                "url": page_url,
                "markdown": markdown_output,
            })

    return format_fetch_results(
        results=formatted_results,
        total_count=len(urls),
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