"""Tests for the formatter module."""

import pytest
from typing import Any

from igloo_mcp.converter import TruncationMetadata
from igloo_mcp.formatter import (
    format_search_results,
    format_fetch_result,
    format_fetch_results,
    format_truncation_metadata,
    _format_header,
    _format_single_result,
    _format_date,
    _truncate_text,
    _format_date_filter,
)


# Note: mock_data_path and sample_search_results fixtures are defined in conftest.py


@pytest.fixture
def sample_results(sample_search_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Alias for sample_search_results for backward compatibility."""
    return sample_search_results


class TestFormatSearchResults:
    """Tests for the main format_search_results function."""

    def test_empty_results(self):
        """Test formatting with no results."""
        result = format_search_results(
            results=[],
            search_params={"query": "test", "sort": "default", "limit": 20},
            total_found=0,
        )
        
        assert "Search Results for Query: \"test\"" in result
        assert "No results found." in result

    def test_single_result(self, sample_results: list[dict]):
        """Test formatting with a single result."""
        single_result = sample_results[0]
        result = format_search_results(
            results=[single_result],
            search_params={"query": "test", "sort": "default", "limit": 20},
            total_found=1,
        )
        
        assert single_result["title"] in result
        assert f"Type: {single_result['type']}" in result
        assert single_result["full_url"] in result
        assert "Last Modified: 2025-09-01" in result
        assert f"Views: {single_result['views_count']} | Comments: {single_result['comments_count']} | Likes: {single_result['likes_count']}" in result
        assert result.count("----------") == 2  # Start and end separators

    def test_multiple_results(self, sample_results: list[dict]):
        """Test formatting with multiple results."""
        result = format_search_results(
            results=sample_results,
            search_params={"query": "test", "sort": "default", "limit": 20},
            total_found=len(sample_results),
        )
        
        for item in sample_results:
            assert item["title"] in result
        
        assert result.count("----------") == len(sample_results) + 1

    def test_result_with_description(self, sample_results: list[dict]):
        """Test formatting result with description."""
        # Find a result with a description
        result_with_desc = next(item for item in sample_results if item.get("description"))
        
        result = format_search_results(
            results=[result_with_desc],
            search_params={"query": "test", "sort": "default", "limit": 20},
            total_found=1,
        )
        
        assert f"Description: {result_with_desc['description']}" in result

    def test_result_with_content(self, sample_results: list[dict]):
        """Test formatting result with content (no description)."""
        result_with_content = {
            "title": "Test With Content",
            "type": "blog",
            "full_url": "https://example.com/content-test",
            "content": "This is a test content.",
            "views_count": 50,
            "comments_count": 2,
            "likes_count": 1,
        }
        
        result = format_search_results(
            results=[result_with_content],
            search_params={"query": "test", "sort": "default", "limit": 20},
            total_found=1,
        )
        
        assert "Content: This is a test content." in result

    def test_result_prefers_description_over_content(self):
        """Test that description is preferred over content when both exist."""
        results = [{
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "description": "Description text",
            "content": "Content text",
            "views_count": 100,
            "comments_count": 5,
            "likes_count": 10,
        }]
        
        result = format_search_results(
            results=results,
            search_params={"query": "test", "sort": "default", "limit": 20},
            total_found=1,
        )
        
        assert "Description: Description text" in result
        assert "Content:" not in result

    def test_result_with_labels(self):
        """Test formatting result with labels."""
        results = [{
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "labels": {"1": "AI", "2": "Cloud", "3": "Guide"},
            "views_count": 100,
            "comments_count": 5,
            "likes_count": 10,
        }]
        
        result = format_search_results(
            results=results,
            search_params={"query": "test", "sort": "default", "limit": 20},
            total_found=1,
        )
        
        assert "Labels: AI, Cloud, Guide" in result

    def test_result_recommended(self):
        """Test formatting result marked as recommended."""
        results = [{
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "is_recommended": True,
            "views_count": 100,
            "comments_count": 5,
            "likes_count": 10,
        }]
        
        result = format_search_results(
            results=results,
            search_params={"query": "test", "sort": "default", "limit": 20},
            total_found=1,
        )
        
        assert "* This item is recommended" in result

    def test_result_archived(self):
        """Test formatting result marked as archived."""
        results = [{
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "is_archived": True,
            "views_count": 100,
            "comments_count": 5,
            "likes_count": 10,
        }]
        
        result = format_search_results(
            results=results,
            search_params={"query": "test", "sort": "default", "limit": 20},
            total_found=1,
        )
        
        assert "* This item is archived" in result

    def test_result_not_recommended_not_shown(self, sample_results: list[dict]):
        """Test that non-recommended items don't show the annotation."""
        result_not_recommended = next(
            item for item in sample_results if not item.get("is_recommended")
        )
        
        result = format_search_results(
            results=[result_not_recommended],
            search_params={"query": "test", "sort": "default", "limit": 20},
            total_found=1,
        )
        
        assert "* This item is recommended" not in result


class TestFormatHeader:
    """Tests for header formatting."""

    def test_basic_header(self):
        """Test basic header with minimal parameters."""
        header = _format_header(
            search_params={"query": "test", "sort": "default", "limit": 20},
            total_found=5,
        )
        
        assert 'Search Results for Query: "test"' in header
        assert "Applications: All" in header
        assert "Sort: default" in header
        assert "Limit: 20" in header
        assert "Total Results Found: 5" in header

    def test_header_no_query(self):
        """Test header with no query."""
        header = _format_header(
            search_params={"sort": "default", "limit": 20},
            total_found=5,
        )
        
        assert "Search Results for Query: All" in header

    def test_header_with_applications(self):
        """Test header with application filters."""
        header = _format_header(
            search_params={
                "query": "test",
                "applications": ["blog", "pages"],
                "sort": "default",
                "limit": 20,
            },
            total_found=5,
        )
        
        assert "Applications: blog, pages" in header

    def test_header_with_parent(self):
        """Test header with parent href."""
        header = _format_header(
            search_params={
                "query": "test",
                "parent_href": "/projects/ai",
                "sort": "default",
                "limit": 20,
            },
            total_found=5,
        )
        
        assert "Parent: /projects/ai" in header

    def test_header_with_date_filter(self):
        """Test header with date filter."""
        header = _format_header(
            search_params={
                "query": "test",
                "updated_date_type": "past_month",
                "sort": "default",
                "limit": 20,
            },
            total_found=5,
        )
        
        assert "Date Filter: Past Month" in header

    def test_header_with_custom_date_range(self):
        """Test header with custom date range."""
        header = _format_header(
            search_params={
                "query": "test",
                "updated_date_type": "custom_range",
                "updated_date_range_from": "2025-01-01",
                "updated_date_range_to": "2025-01-31",
                "sort": "default",
                "limit": 20,
            },
            total_found=5,
        )
        
        assert "Date Filter: 2025-01-01 to 2025-01-31" in header

    def test_header_with_views_sort(self):
        """Test header with views sorting."""
        header = _format_header(
            search_params={
                "query": "test",
                "sort": "views",
                "limit": 20,
            },
            total_found=5,
        )
        
        assert "Sort: views" in header

    def test_header_no_limit(self):
        """Test header with no limit."""
        header = _format_header(
            search_params={
                "query": "test",
                "sort": "default",
            },
            total_found=5,
        )
        
        assert "Limit: None" in header

    def test_header_with_empty_applications_list(self):
        """Test header with empty applications list displays 'All'."""
        header = _format_header(
            search_params={
                "query": "test",
                "applications": [],
                "sort": "default",
                "limit": 20,
            },
            total_found=5,
        )
        
        assert "Applications: All" in header

    def test_header_with_very_long_parent_href(self):
        """Test header with very long parent href (500+ characters)."""
        long_parent_href = "/projects/" + "a" * 500
        header = _format_header(
            search_params={
                "query": "test",
                "parent_href": long_parent_href,
                "sort": "default",
                "limit": 20,
            },
            total_found=5,
        )
        
        assert f"Parent: {long_parent_href}" in header

    def test_header_with_all_optional_parameters(self):
        """Test header with all optional parameters present simultaneously."""
        header = _format_header(
            search_params={
                "query": "test",
                "applications": ["blog", "pages", "documents"],
                "parent_href": "/projects/ai/ml",
                "updated_date_type": "past_week",
                "sort": "views",
                "limit": 50,
            },
            total_found=42,
        )
        
        assert 'Search Results for Query: "test"' in header
        assert "Applications: blog, pages, documents" in header
        assert "Parent: /projects/ai/ml" in header
        assert "Date Filter: Past Week" in header
        assert "Sort: views" in header
        assert "Limit: 50" in header
        assert "Total Results Found: 42" in header

    def test_header_with_limit_zero(self):
        """Test header with limit explicitly set to 0."""
        header = _format_header(
            search_params={
                "query": "test",
                "sort": "default",
                "limit": 0,
            },
            total_found=5,
        )
        
        assert "Limit: 0" in header


class TestFormatSingleResult:
    """Tests for formatting individual results."""

    def test_minimal_result(self):
        """Test formatting a minimal result with only required fields."""
        result = _format_single_result({
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "views_count": 10,
            "comments_count": 2,
            "likes_count": 1,
        })
        
        assert "Title: Test" in result
        assert "Type: blog" in result
        assert "URL: https://example.com/test" in result
        assert "Views: 10 | Comments: 2 | Likes: 1" in result

    def test_result_missing_title(self):
        """Test formatting result with missing title."""
        result = _format_single_result({
            "type": "blog",
            "full_url": "https://example.com/test",
            "views_count": 10,
            "comments_count": 2,
            "likes_count": 1,
        })
        
        assert "Title: Untitled" in result

    def test_result_missing_metrics(self):
        """Test formatting result with missing metrics."""
        result = _format_single_result({
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
        })
        
        assert "Views: 0 | Comments: 0 | Likes: 0" in result

    def test_result_with_empty_labels_dict(self):
        """Test that empty labels dict doesn't show labels line."""
        result = _format_single_result({
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "labels": {},
            "views_count": 10,
            "comments_count": 2,
            "likes_count": 1,
        })
        
        assert "Labels:" not in result

    def test_result_with_none_description(self):
        """Test formatting result with None description value."""
        result = _format_single_result({
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "description": None,
            "views_count": 10,
            "comments_count": 2,
            "likes_count": 1,
        })
        
        assert "Description:" not in result

    def test_result_with_none_content(self):
        """Test formatting result with None content value."""
        result = _format_single_result({
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "content": None,
            "views_count": 10,
            "comments_count": 2,
            "likes_count": 1,
        })
        
        assert "Content:" not in result

    def test_result_with_none_modified_date(self):
        """Test formatting result with None modified_date value."""
        result = _format_single_result({
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "modified_date": None,
            "views_count": 10,
            "comments_count": 2,
            "likes_count": 1,
        })
        
        assert "Last Modified:" not in result

    def test_result_with_none_labels(self):
        """Test formatting result with None labels value."""
        result = _format_single_result({
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "labels": None,
            "views_count": 10,
            "comments_count": 2,
            "likes_count": 1,
        })
        
        assert "Labels:" not in result

    def test_result_with_very_long_labels_list(self):
        """Test formatting result with very long labels list (100+ items)."""
        labels_dict = {str(i): f"Label{i}" for i in range(1, 101)}
        result = _format_single_result({
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "labels": labels_dict,
            "views_count": 10,
            "comments_count": 2,
            "likes_count": 1,
        })
        
        assert "Labels:" in result
        # Verify it contains multiple labels
        assert "Label1" in result
        assert "Label50" in result
        assert "Label100" in result

    def test_result_with_numeric_only_labels(self):
        """Test formatting result with labels having only numeric values."""
        result = _format_single_result({
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "labels": {"1": 123, "2": 456, "3": 789},
            "views_count": 10,
            "comments_count": 2,
            "likes_count": 1,
        })
        
        assert "Labels:" in result
        assert "123" in result
        assert "456" in result
        assert "789" in result

    def test_result_both_recommended_and_archived(self):
        """Test formatting result with both is_recommended and is_archived set to True."""
        result = _format_single_result({
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "is_recommended": True,
            "is_archived": True,
            "views_count": 10,
            "comments_count": 2,
            "likes_count": 1,
        })
        
        assert "* This item is recommended" in result
        assert "* This item is archived" in result

    def test_result_missing_modified_date_field(self):
        """Test formatting result without modified_date field entirely."""
        result = _format_single_result({
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "views_count": 10,
            "comments_count": 2,
            "likes_count": 1,
        })
        
        assert "Last Modified:" not in result

    def test_result_empty_string_vs_none_description(self):
        """Test distinction between empty string and None for description."""
        result_empty = _format_single_result({
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "description": "",
            "views_count": 10,
            "comments_count": 2,
            "likes_count": 1,
        })
        
        assert "Description:" not in result_empty

    def test_result_empty_string_vs_none_content(self):
        """Test distinction between empty string and None for content."""
        result_empty = _format_single_result({
            "title": "Test",
            "type": "blog",
            "full_url": "https://example.com/test",
            "content": "",
            "views_count": 10,
            "comments_count": 2,
            "likes_count": 1,
        })
        
        assert "Content:" not in result_empty

    def test_result_url_with_special_characters(self):
        """Test formatting result with URL containing special characters."""
        special_url = "https://example.com/test?param=value&foo=bar#section"
        result = _format_single_result({
            "title": "Test",
            "type": "blog",
            "full_url": special_url,
            "views_count": 10,
            "comments_count": 2,
            "likes_count": 1,
        })
        
        assert f"URL: {special_url}" in result


class TestFormatDate:
    """Tests for date formatting."""

    def test_iso_datetime_with_timezone(self):
        """Test parsing ISO datetime with timezone."""
        formatted = _format_date("2025-11-06T14:20:28.85-05:00")
        assert formatted == "2025-11-06"

    def test_iso_datetime_utc(self):
        """Test parsing ISO datetime in UTC."""
        formatted = _format_date("2025-11-06T14:20:28Z")
        assert formatted == "2025-11-06"

    def test_simple_date(self):
        """Test simple date string."""
        formatted = _format_date("2025-11-06")
        assert formatted == "2025-11-06"

    def test_invalid_date(self):
        """Test handling of invalid date."""
        formatted = _format_date("invalid-date")
        assert formatted == "invalid-date"

    def test_short_string(self):
        """Test handling of short string that can't be a date."""
        formatted = _format_date("short")
        assert formatted == "short"

    def test_iso_datetime_with_microseconds(self):
        """Test parsing ISO datetime with microseconds."""
        formatted = _format_date("2025-11-06T14:20:28.123456Z")
        assert formatted == "2025-11-06"

    @pytest.mark.parametrize("date_input,expected", [
        ("2025-11-06T14:20:28+05:30", "2025-11-06"),  # Timezone +0530
        ("2025-11-06T14:20:28+05:30", "2025-11-06"),  # Timezone +05:30 format
        ("2025-11-06T14:20:28-08:00", "2025-11-06"),  # Timezone -0800
    ])
    def test_different_timezone_formats(self, date_input: str, expected: str):
        """Test parsing ISO datetime with different timezone formats."""
        formatted = _format_date(date_input)
        assert formatted == expected

    @pytest.mark.parametrize("date_input,expected", [
        ("1999-12-31T23:59:59Z", "1999-12-31"),  # Year boundary: 1999 end
        ("2000-01-01T00:00:00Z", "2000-01-01"),  # Year boundary: 2000 start
    ])
    def test_year_boundaries(self, date_input: str, expected: str):
        """Test parsing dates at year boundaries."""
        formatted = _format_date(date_input)
        assert formatted == expected

    def test_leap_year_date(self):
        """Test parsing leap year date (Feb 29, 2024)."""
        formatted = _format_date("2024-02-29T12:00:00Z")
        assert formatted == "2024-02-29"

    def test_invalid_month(self):
        """Test handling of invalid month (13) - extracts first 10 chars as fallback."""
        formatted = _format_date("2025-13-01T12:00:00Z")
        assert formatted == "2025-13-01"

    def test_empty_string_input(self):
        """Test handling of empty string input."""
        formatted = _format_date("")
        assert formatted == ""



class TestTruncateText:
    """Tests for text truncation."""

    def test_short_text_not_truncated(self):
        """Test that short text is not truncated."""
        text = "This is a short text"
        truncated = _truncate_text(text, max_length=200)
        assert truncated == text

    def test_long_text_truncated(self):
        """Test that long text is truncated."""
        text = "a" * 250
        truncated = _truncate_text(text, max_length=200)
        assert len(truncated) <= 203  # 200 + "..."
        assert truncated.endswith("...")

    def test_truncation_at_word_boundary(self):
        """Test that truncation happens at word boundaries."""
        text = "This is a very long text " * 20
        truncated = _truncate_text(text, max_length=50)
        
        assert truncated.endswith("...")
        before_ellipsis = truncated[:-3]
        assert not before_ellipsis.endswith(" ")

    def test_exact_length_not_truncated(self):
        """Test that text at exact max length is not truncated."""
        text = "a" * 200
        truncated = _truncate_text(text, max_length=200)
        assert truncated == text

    def test_text_exactly_at_max_length(self):
        """Test text exactly at max_length (200 characters)."""
        text = "a" * 200
        truncated = _truncate_text(text, max_length=200)
        assert len(truncated) == 200
        assert not truncated.endswith("...")

    def test_text_with_only_spaces(self):
        """Test text containing only spaces."""
        text = " " * 250
        truncated = _truncate_text(text, max_length=200)
        assert len(truncated) <= 203

    def test_text_with_no_spaces(self):
        """Test text with no spaces (single long word)."""
        text = "a" * 250
        truncated = _truncate_text(text, max_length=200)
        assert len(truncated) <= 203
        assert truncated.endswith("...")

    def test_unicode_emoji_characters(self):
        """Test text with unicode/emoji characters."""
        text = "Hello 👋 World " * 30
        truncated = _truncate_text(text, max_length=200)
        assert len(truncated) <= 203
        if len(text) > 200:
            assert truncated.endswith("...")

    def test_text_ending_with_multiple_spaces(self):
        """Test text ending with multiple spaces before truncation."""
        text = "word " * 50  # Creates text with spaces
        truncated = _truncate_text(text, max_length=50)
        assert truncated.endswith("...")
        before_ellipsis = truncated[:-3]
        assert not before_ellipsis.endswith(" ")


class TestFormatDateFilter:
    """Tests for date filter formatting."""

    def test_past_hour(self):
        """Test formatting past_hour filter."""
        result = _format_date_filter("past_hour", {})
        assert result == "Date Filter: Past Hour"

    def test_past_month(self):
        """Test formatting past_month filter."""
        result = _format_date_filter("past_month", {})
        assert result == "Date Filter: Past Month"

    def test_custom_range_with_dates(self):
        """Test formatting custom_range with dates provided."""
        result = _format_date_filter(
            "custom_range",
            {
                "updated_date_range_from": "2025-01-01",
                "updated_date_range_to": "2025-01-31",
            }
        )
        assert result == "Date Filter: 2025-01-01 to 2025-01-31"

    def test_custom_range_without_dates(self):
        """Test formatting custom_range without dates."""
        result = _format_date_filter("custom_range", {})
        assert result == "Date Filter: Custom Range"

    def test_custom_range_with_only_from_date(self):
        """Test formatting custom_range with only updated_date_range_from."""
        result = _format_date_filter(
            "custom_range",
            {
                "updated_date_range_from": "2025-01-01",
            }
        )
        assert result == "Date Filter: Custom Range"

    def test_custom_range_with_only_to_date(self):
        """Test formatting custom_range with only updated_date_range_to."""
        result = _format_date_filter(
            "custom_range",
            {
                "updated_date_range_to": "2025-01-31",
            }
        )
        assert result == "Date Filter: Custom Range"

    def test_invalid_unknown_date_type(self):
        """Test formatting with invalid/unknown date_type string."""
        result = _format_date_filter("unknown_filter_type", {})
        assert result == "Date Filter: Unknown Filter Type"


class TestFormatFetchResults:
    """Tests for the format_fetch_results function (multiple pages)."""

    def test_empty_results(self):
        """Test formatting with no results."""
        result = format_fetch_results(results=[], total_count=0)
        assert result == "No pages to display."

    def test_single_page_success(self):
        """Test formatting a single successful page."""
        results = [{
            "url": "https://example.com/wiki/page1",
            "markdown": "# Page 1\n\nThis is the content.",
        }]
        
        result = format_fetch_results(results=results, total_count=1)
        
        assert "===== PAGE 1 of 1 =====" in result
        assert "URL: https://example.com/wiki/page1" in result
        assert "# Page 1" in result
        assert "This is the content." in result

    def test_multiple_pages_success(self):
        """Test formatting multiple successful pages."""
        results = [
            {
                "url": "https://example.com/wiki/page1",
                "markdown": "# Page 1 Content",
            },
            {
                "url": "https://example.com/wiki/page2",
                "markdown": "# Page 2 Content",
            },
            {
                "url": "https://example.com/wiki/page3",
                "markdown": "# Page 3 Content",
            },
        ]
        
        result = format_fetch_results(results=results, total_count=3)
        
        assert "===== PAGE 1 of 3 =====" in result
        assert "===== PAGE 2 of 3 =====" in result
        assert "===== PAGE 3 of 3 =====" in result
        assert "URL: https://example.com/wiki/page1" in result
        assert "URL: https://example.com/wiki/page2" in result
        assert "URL: https://example.com/wiki/page3" in result
        assert "# Page 1 Content" in result
        assert "# Page 2 Content" in result
        assert "# Page 3 Content" in result

    def test_page_with_error(self):
        """Test formatting a page that has an error."""
        results = [{
            "url": "https://example.com/wiki/failed-page",
            "error": "HTTP 404 - Failed to fetch page",
        }]
        
        result = format_fetch_results(results=results, total_count=1)
        
        assert "===== PAGE 1 of 1 =====" in result
        assert "URL: https://example.com/wiki/failed-page" in result
        assert "[Error fetching page: HTTP 404 - Failed to fetch page]" in result

    def test_mixed_success_and_errors(self):
        """Test formatting mix of successful and failed pages."""
        results = [
            {
                "url": "https://example.com/wiki/page1",
                "markdown": "# Success Content",
            },
            {
                "url": "https://example.com/wiki/failed",
                "error": "Request timed out",
            },
            {
                "url": "https://example.com/wiki/page3",
                "markdown": "# Another Success",
            },
        ]
        
        result = format_fetch_results(results=results, total_count=3)
        
        assert "===== PAGE 1 of 3 =====" in result
        assert "===== PAGE 2 of 3 =====" in result
        assert "===== PAGE 3 of 3 =====" in result
        assert "# Success Content" in result
        assert "[Error fetching page: Request timed out]" in result
        assert "# Another Success" in result

    def test_missing_url(self):
        """Test formatting result with missing URL field."""
        results = [{
            "markdown": "# Content without URL",
        }]
        
        result = format_fetch_results(results=results, total_count=1)
        
        assert "URL: Unknown URL" in result
        assert "# Content without URL" in result

    def test_missing_markdown(self):
        """Test formatting result with missing markdown field."""
        results = [{
            "url": "https://example.com/wiki/page",
        }]
        
        result = format_fetch_results(results=results, total_count=1)
        
        assert "URL: https://example.com/wiki/page" in result
        # Should have empty content, not error

    def test_all_errors(self):
        """Test formatting when all pages have errors."""
        results = [
            {
                "url": "https://example.com/wiki/page1",
                "error": "HTTP 500 - Server Error",
            },
            {
                "url": "https://example.com/wiki/page2",
                "error": "Connection refused",
            },
        ]
        
        result = format_fetch_results(results=results, total_count=2)
        
        assert "===== PAGE 1 of 2 =====" in result
        assert "===== PAGE 2 of 2 =====" in result
        assert "[Error fetching page: HTTP 500 - Server Error]" in result
        assert "[Error fetching page: Connection refused]" in result

    def test_large_content(self):
        """Test formatting with large markdown content."""
        large_content = "# Header\n\n" + "This is a paragraph. " * 1000
        results = [{
            "url": "https://example.com/wiki/large-page",
            "markdown": large_content,
        }]
        
        result = format_fetch_results(results=results, total_count=1)
        
        assert "===== PAGE 1 of 1 =====" in result
        assert large_content in result

    def test_unicode_content(self):
        """Test formatting with unicode content."""
        results = [{
            "url": "https://example.com/wiki/unicode",
            "markdown": "# 日本語タイトル\n\nこれは日本語のコンテンツです。",
        }]
        
        result = format_fetch_results(results=results, total_count=1)
        
        assert "日本語タイトル" in result
        assert "日本語のコンテンツ" in result

    def test_special_url_characters(self):
        """Test formatting with URLs containing special characters."""
        results = [{
            "url": "https://example.com/wiki/page?param=value&foo=bar#section",
            "markdown": "# Content",
        }]
        
        result = format_fetch_results(results=results, total_count=1)
        
        assert "URL: https://example.com/wiki/page?param=value&foo=bar#section" in result


class TestFormatTruncationMetadata:
    """Tests for the format_truncation_metadata function."""

    def test_basic_metadata(self):
        """Test formatting with minimal metadata."""
        metadata = TruncationMetadata(
            status="partial",
            chars_returned=1000,
            chars_total=5000,
            next_start_index=1000,
        )
        url = "https://example.com/wiki/page"
        
        result = format_truncation_metadata(metadata, url)
        
        assert "⚠️ CONTENT TRUNCATED" in result
        assert "Showing 1,000 of 5,000 chars (20% of document)" in result
        assert "To continue reading, call fetch with start_index:" in result
        assert 'fetch(url="https://example.com/wiki/page", start_index=1000)' in result

    def test_metadata_with_current_path(self):
        """Test formatting with current section path."""
        metadata = TruncationMetadata(
            status="partial",
            chars_returned=5000,
            chars_total=20000,
            next_start_index=5000,
            current_path="Documentation > API Reference",
        )
        url = "https://example.com/docs"
        
        result = format_truncation_metadata(metadata, url)
        
        assert "Current section: Documentation > API Reference" in result

    def test_metadata_with_remaining_sections(self):
        """Test formatting with remaining sections list."""
        metadata = TruncationMetadata(
            status="partial",
            chars_returned=10000,
            chars_total=50000,
            next_start_index=10000,
            remaining_sections=["Rate Limits", "Error Codes", "Webhooks"],
        )
        url = "https://example.com/api-docs"
        
        result = format_truncation_metadata(metadata, url)
        
        assert "Upcoming sections: Rate Limits, Error Codes, Webhooks" in result

    def test_metadata_full(self):
        """Test formatting with all fields populated."""
        metadata = TruncationMetadata(
            status="partial",
            chars_returned=49800,
            chars_total=125000,
            next_start_index=49800,
            current_path="Docs > API > Authentication",
            remaining_sections=["Rate Limits", "Error Codes", "Webhooks", "Examples", "FAQ"],
        )
        url = "https://igloo.example.com/wiki/api-documentation"
        
        result = format_truncation_metadata(metadata, url)
        
        assert "---" in result
        assert "⚠️ CONTENT TRUNCATED" in result
        assert "Showing 49,800 of 125,000 chars (39% of document)" in result
        assert "Current section: Docs > API > Authentication" in result
        assert "Upcoming sections: Rate Limits, Error Codes, Webhooks, Examples, FAQ" in result
        assert "To continue reading, call fetch with start_index:" in result
        assert 'fetch(url="https://igloo.example.com/wiki/api-documentation", start_index=49800)' in result

    def test_metadata_no_next_index(self):
        """Test formatting when next_start_index is None."""
        metadata = TruncationMetadata(
            status="partial",
            chars_returned=1000,
            chars_total=5000,
            next_start_index=None,
        )
        url = "https://example.com/page"
        
        result = format_truncation_metadata(metadata, url)
        
        assert "⚠️ CONTENT TRUNCATED" in result
        assert "Showing 1,000 of 5,000 chars (20% of document)" in result
        assert "To continue reading" not in result

    def test_metadata_empty_remaining_sections(self):
        """Test formatting with empty remaining sections list."""
        metadata = TruncationMetadata(
            status="partial",
            chars_returned=4500,
            chars_total=5000,
            next_start_index=4500,
            remaining_sections=[],
        )
        url = "https://example.com/page"
        
        result = format_truncation_metadata(metadata, url)
        
        assert "Upcoming sections:" not in result

    def test_metadata_large_numbers_formatted(self):
        """Test that large numbers are properly formatted with commas."""
        metadata = TruncationMetadata(
            status="partial",
            chars_returned=1234567,
            chars_total=9876543,
            next_start_index=1234567,
        )
        url = "https://example.com/large-doc"
        
        result = format_truncation_metadata(metadata, url)
        
        assert "Showing 1,234,567 of 9,876,543 chars" in result

    def test_metadata_url_with_special_characters(self):
        """Test formatting with URL containing special characters."""
        metadata = TruncationMetadata(
            status="partial",
            chars_returned=1000,
            chars_total=5000,
            next_start_index=1000,
        )
        url = "https://example.com/page?query=test&filter=active"
        
        result = format_truncation_metadata(metadata, url)
        
        assert "To continue reading, call fetch with start_index:" in result
        assert '  fetch(url="https://example.com/page?query=test&filter=active", start_index=1000)' in result

    def test_metadata_starts_with_separator(self):
        """Test that output starts with newlines and separator."""
        metadata = TruncationMetadata(
            status="partial",
            chars_returned=1000,
            chars_total=5000,
            next_start_index=1000,
        )
        url = "https://example.com/page"
        
        result = format_truncation_metadata(metadata, url)
        
        # Should start with newline, separator
        lines = result.split('\n')
        assert lines[0] == ""  # Empty first line
        assert lines[1] == "---"  # Separator

    def test_continuation_indentation(self):
        """Test that fetch command in continuation instructions is indented with 2 spaces."""
        metadata = TruncationMetadata(
            status="partial",
            chars_returned=1000,
            chars_total=5000,
            next_start_index=1000,
            current_path="Section A",
            remaining_sections=["Section B", "Section C"],
        )
        url = "https://example.com/page"
        
        result = format_truncation_metadata(metadata, url)
        
        # Should have continuation instructions with indented fetch command
        assert "To continue reading, call fetch with start_index:" in result
        assert '  fetch(url="https://example.com/page", start_index=1000)' in result
        # Should NOT use table format
        assert "|" not in result

    def test_percentage_calculation(self):
        """Test that percentage is calculated correctly."""
        metadata = TruncationMetadata(
            status="partial",
            chars_returned=1000,
            chars_total=5000,
            next_start_index=1000,
        )
        url = "https://example.com/page"
        
        result = format_truncation_metadata(metadata, url)
        
        # 1000 / 5000 = 20%
        assert "(20% of document)" in result

    def test_percentage_zero_total(self):
        """Test edge case where chars_total is 0 should return 0% without error."""
        metadata = TruncationMetadata(
            status="partial",
            chars_returned=0,
            chars_total=0,
            next_start_index=None,
        )
        url = "https://example.com/page"
        
        result = format_truncation_metadata(metadata, url)
        
        # Should handle divide-by-zero gracefully
        assert "(0% of document)" in result


class TestFormatFetchResult:
    """Tests for the format_fetch_result function (single page formatting)."""

    def test_basic_formatting(self):
        """Test basic fetch result formatting."""
        result = format_fetch_result(
            url="https://example.com/wiki/page",
            markdown="# Title\n\nContent here.",
        )
        
        assert "# Fetched Content" in result
        assert "URL: https://example.com/wiki/page" in result
        assert "---" in result
        assert "# Title" in result
        assert "Content here." in result

    def test_format_without_offset(self):
        """Test format_fetch_result without offset shows normal header."""
        result = format_fetch_result(
            url="https://example.com/page",
            markdown="# Test\n\nContent here.",
        )
        
        assert "URL: https://example.com/page" in result
        assert "Reading from offset" not in result

    def test_format_with_offset(self):
        """Test format_fetch_result with offset shows position context."""
        result = format_fetch_result(
            url="https://example.com/page",
            markdown="Continued content here.",
            start_index=5000,
        )
        
        assert "URL: https://example.com/page" in result
        assert "Reading from offset: 5,000" in result

    def test_format_with_zero_offset(self):
        """Test format_fetch_result with zero offset shows no position."""
        result = format_fetch_result(
            url="https://example.com/page",
            markdown="Content.",
            start_index=0,
        )
        
        assert "Reading from offset" not in result

    def test_format_with_large_offset(self):
        """Test format_fetch_result formats large offsets with commas."""
        result = format_fetch_result(
            url="https://example.com/page",
            markdown="Content.",
            start_index=1234567,
        )
        
        assert "Reading from offset: 1,234,567" in result

    def test_url_with_special_characters(self):
        """Test formatting URL with query params and fragments."""
        result = format_fetch_result(
            url="https://example.com/page?param=value&foo=bar#section",
            markdown="Content.",
        )
        
        assert "URL: https://example.com/page?param=value&foo=bar#section" in result

    def test_empty_markdown(self):
        """Test formatting with empty markdown content."""
        result = format_fetch_result(
            url="https://example.com/page",
            markdown="",
        )
        
        assert "URL: https://example.com/page" in result
        assert "---" in result

    def test_unicode_content(self):
        """Test formatting with unicode/international content."""
        result = format_fetch_result(
            url="https://example.com/wiki/unicode",
            markdown="# 日本語タイトル\n\nこれは日本語のコンテンツです。",
        )
        
        assert "日本語タイトル" in result
        assert "日本語のコンテンツ" in result

    def test_very_long_url(self):
        """Test formatting with very long URL."""
        long_url = "https://example.com/" + "a" * 500 + "/page"
        result = format_fetch_result(
            url=long_url,
            markdown="Content.",
        )
        
        assert f"URL: {long_url}" in result

    def test_markdown_with_code_blocks(self):
        """Test formatting markdown that contains code blocks."""
        markdown_with_code = """# API Reference

```python
def hello():
    print("Hello, World!")
```

More content here.
"""
        result = format_fetch_result(
            url="https://example.com/docs",
            markdown=markdown_with_code,
        )
        
        assert "```python" in result
        assert 'print("Hello, World!")' in result

    def test_output_structure(self):
        """Test the overall structure of the output."""
        result = format_fetch_result(
            url="https://example.com/page",
            markdown="# Title\n\nBody text.",
        )
        
        lines = result.split("\n")
        # Should have: # Fetched Content, empty line, URL, empty line, ---, empty lines, content
        assert lines[0] == "# Fetched Content"
        assert "URL:" in result
        assert "---" in result