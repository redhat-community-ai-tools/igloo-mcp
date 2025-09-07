"""Formatter for search results to create token-efficient, human-readable output."""

from datetime import datetime
from typing import Any


def format_search_results(
    results: list[dict[str, Any]],
    search_params: dict[str, Any],
    total_found: int,
) -> str:
    """
    Format search results into a concise, human-readable string optimized for LLM token efficiency.

    Args:
        results: List of search result dictionaries with fields like title, type, url, etc.
        search_params: Dictionary containing the search parameters used (query, applications, etc.)
        total_found: Total number of results found by the search

    Returns:
        A formatted string containing the search results with header and individual result sections.
    """
    header = _format_header(search_params, total_found)
    
    if not results:
        return f"{header}\n\nNo results found."
    
    formatted_results = [header]
    
    for result in results:
        formatted_results.append("\n----------\n")
        formatted_results.append(_format_single_result(result))
    
    formatted_results.append("\n----------")
    
    return "".join(formatted_results)


def _format_header(search_params: dict[str, Any], total_found: int) -> str:
    """Format search results header with query parameters."""
    query = search_params.get("query")
    query_str = f'"{query}"' if query else "All"
    
    applications = search_params.get("applications")
    if applications:
        apps_str = ", ".join(applications)
    else:
        apps_str = "All"
    
    sort = search_params.get("sort", "default")
    
    limit = search_params.get("limit")
    limit_str = str(limit) if limit is not None else "None"
    
    header_parts = [
        f"Applications: {apps_str}",
        f"Sort: {sort}",
        f"Limit: {limit_str}",
        f"Total Results Found: {total_found}",
    ]
    
    parent_href = search_params.get("parent_href")
    if parent_href:
        header_parts.insert(1, f"Parent: {parent_href}")
    
    updated_date_type = search_params.get("updated_date_type")
    if updated_date_type:
        date_filter = _format_date_filter(updated_date_type, search_params)
        header_parts.insert(1, date_filter)
    
    header = f"Search Results for Query: {query_str} ({' | '.join(header_parts)}):"
    
    return header


def _format_date_filter(updated_date_type: str, search_params: dict[str, Any]) -> str:
    """Format the date filter information for the header."""
    if updated_date_type == "custom_range":
        date_from = search_params.get("updated_date_range_from")
        date_to = search_params.get("updated_date_range_to")
        if date_from and date_to:
            return f"Date Filter: {date_from} to {date_to}"
        return "Date Filter: Custom Range"
    
    date_type_display = updated_date_type.replace("_", " ").title()
    return f"Date Filter: {date_type_display}"


def _format_single_result(result: dict[str, Any]) -> str:
    """Format a single search result."""
    lines = []
    
    lines.append(f"Title: {result.get('title', 'Untitled')}")
    lines.append(f"Type: {result.get('type', 'unknown')}")
    lines.append(f"URL: {result.get('full_url', '')}")
    
    modified_date = result.get("modified_date")
    if modified_date:
        formatted_date = _format_date(modified_date)
        lines.append(f"Last Modified: {formatted_date}")
    
    description = (result.get("description") or "").strip()
    content = (result.get("content") or "").strip()
    
    text_to_show = description or content
    if text_to_show:
        truncated_text = _truncate_text(text_to_show, max_length=200)
        field_name = "Description" if description else "Content"
        lines.append(f"{field_name}: {truncated_text}")
    
    views = result.get("views_count", 0)
    comments = result.get("comments_count", 0)
    likes = result.get("likes_count", 0)
    lines.append(f"Views: {views} | Comments: {comments} | Likes: {likes}")
    
    labels = result.get("labels", {})
    if labels:
        label_names = [str(name) for name in labels.values()]
        if label_names:
            lines.append(f"Labels: {', '.join(label_names)}")
    
    if result.get("is_recommended"):
        lines.append("* This item is recommended")
    
    if result.get("is_archived"):
        lines.append("* This item is archived")
    
    return "\n".join(lines)


def _format_date(date_str: str) -> str:
    """
    Parse an ISO format date string and return it in YYYY-MM-DD format.
    
    Args:
        date_str: ISO format date string (e.g., "2025-11-06T14:20:28.85-05:00")
    
    Returns:
        Date in YYYY-MM-DD format, or the original string if parsing fails
    """
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime(r"%Y-%m-%d")
    except (ValueError, AttributeError):
        if isinstance(date_str, str) and len(date_str) >= 10 and date_str[4] == "-" and date_str[7] == "-":
            return date_str[:10]
        return str(date_str)


def _truncate_text(text: str, max_length: int = 200) -> str:
    """
    Truncate text to a maximum length, adding ellipsis if truncated.
    
    Args:
        text: The text to truncate
        max_length: Maximum length (default 200)
    
    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    
    truncated = text[:max_length].rsplit(" ", 1)[0]
    return f"{truncated}..."