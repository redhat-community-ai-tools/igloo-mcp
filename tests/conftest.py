"""Shared fixtures and helpers for test suite."""

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def mock_data_path() -> Path:
    """Returns path to mock data directory."""
    return Path(__file__).parent / "tests_data" / "mock_data"


@pytest.fixture
def sample_search_results(mock_data_path: Path) -> list[dict[str, Any]]:
    """Load and transform sample search results from mock data file."""
    with open(mock_data_path / "search_single_page.json", "r") as f:
        mock_data = json.load(f)
    return transform_raw_search_results(mock_data["results"])


@pytest.fixture
def sample_search_results_raw(mock_data_path: Path) -> list[dict[str, Any]]:
    """Load raw sample search results from mock data file (untransformed)."""
    with open(mock_data_path / "search_single_page.json", "r") as f:
        mock_data = json.load(f)
    return mock_data["results"]


def transform_raw_search_results(
    raw_results: list[dict[str, Any]],
    community_url: str = "https://example.com",
) -> list[dict[str, Any]]:
    """
    Transform raw search results from the mock file into the format
    expected by the application's internal functions.

    Args:
        raw_results: Raw results from the Igloo API (mock or real).
        community_url: Base URL of the community for constructing full URLs.

    Returns:
        List of transformed result dictionaries with standardized field names.
    """
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

    return [
        {
            **{
                fields_mapping[key]: value
                for key, value in item.items()
                if key in fields_mapping
            },
            "full_url": f"{community_url}{item['href']}",
        }
        for item in raw_results
    ]
