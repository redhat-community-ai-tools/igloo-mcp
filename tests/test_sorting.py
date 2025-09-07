import json
import pytest
from pathlib import Path
from igloo_mcp.sorting import sort_results


@pytest.fixture
def mock_data_path() -> Path:
    """Returns path to mock data directory."""
    return Path(__file__).parent / "tests_data" / "mock_data"


@pytest.fixture
def sample_results(mock_data_path: Path) -> list[dict]:
    """Load and transform sample search results for sorting tests."""
    with open(mock_data_path / "search_single_page.json", "r") as f:
        mock_data = json.load(f)
    return _transform_raw_results(mock_data["results"])


def _transform_raw_results(raw_results: list[dict]) -> list[dict]:
    """
    Transforms raw search results from the mock file into the format
    expected by the application's internal functions.
    """
    fields_mapping = {
        "id": "id",
        "numberOfViews": "views_count",
    }
    return [
        {fields_mapping[key]: value for key, value in item.items() if key in fields_mapping}
        for item in raw_results
    ]


# ============================================================================
# EXISTING TESTS (4 tests)
# ============================================================================

def test_sort_by_default(sample_results: list[dict]):
    """Tests that the default sort option does not mutate the list."""
    original_data = sample_results.copy()
    sorted_results = sort_results(results=sample_results, sort_by="default")
    assert sorted_results is sample_results
    assert sorted_results == original_data


def test_sort_by_views(sample_results: list[dict]):
    """Tests that the results are sorted by views_count in descending order."""
    sorted_results = sort_results(results=sample_results, sort_by="views")
    
    expected_order_ids = [
        "46fd4d15-f9bb-47c8-a8b6-d57bff7e7070",
        "8ff6aaec-f11b-4713-a7c2-1703bcf8b938",
        "e93d8505-a006-4cd8-9cd4-222e368a4edf",
        "7f42a417-362c-4b4d-a69a-05d91d80e5f3",
        "0d993dea-155d-46f2-ab27-d29a7510fbcd",
        "e71e78b3-bf38-476c-a7b9-acae80992873",
    ]
    
    sorted_ids = [result["id"] for result in sorted_results]
    
    assert sorted_ids == expected_order_ids


def test_sort_by_views_empty_list():
    """Tests sorting an empty list, which should return an empty list."""
    sorted_results = sort_results(results=[], sort_by="views")
    assert sorted_results == []


def test_sort_by_views_all_missing_views_count():
    """Tests sorting a list where all items are missing the views_count key."""
    results = [{"id": 1}, {"id": 2}, {"id": 3}]
    sorted_results = sort_results(results=results, sort_by="views")
    assert sorted_results == results


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

# Basic Edge Cases (4 tests)

def test_sort_by_views_single_item():
    """Test sorting a list with only one item."""
    results = [{"id": "solo", "views_count": 42}]
    sorted_results = sort_results(results=results, sort_by="views")
    
    assert len(sorted_results) == 1
    assert sorted_results[0]["id"] == "solo"
    assert sorted_results[0]["views_count"] == 42


def test_sort_by_views_all_same_count():
    """Test sorting when all items have identical views_count (verify sort stability)."""
    results = [
        {"id": "first", "views_count": 100},
        {"id": "second", "views_count": 100},
        {"id": "third", "views_count": 100},
    ]
    sorted_results = sort_results(results=results, sort_by="views")
    
    assert [r["id"] for r in sorted_results] == ["first", "second", "third"]


def test_sort_by_views_already_sorted_descending():
    """Test sorting a list that is already in correct descending order."""
    results = [
        {"id": "a", "views_count": 1000},
        {"id": "b", "views_count": 500},
        {"id": "c", "views_count": 100},
    ]
    sorted_results = sort_results(results=results, sort_by="views")
    
    assert [r["id"] for r in sorted_results] == ["a", "b", "c"]
    assert [r["views_count"] for r in sorted_results] == [1000, 500, 100]


def test_sort_by_views_already_sorted_ascending():
    """Test sorting a list that is in reverse (ascending) order."""
    results = [
        {"id": "a", "views_count": 100},
        {"id": "b", "views_count": 500},
        {"id": "c", "views_count": 1000},
    ]
    sorted_results = sort_results(results=results, sort_by="views")
    
    assert [r["id"] for r in sorted_results] == ["c", "b", "a"]
    assert [r["views_count"] for r in sorted_results] == [1000, 500, 100]


# Numeric Edge Cases (3 tests)

def test_sort_by_views_with_none_values():
    """Test that sorting raises TypeError when views_count contains None values.
    
    This documents a limitation in the current implementation: when views_count
    is explicitly None (key exists with None value), item.get("views_count", 0)
    returns None instead of 0, causing Python's sorted() to fail when comparing
    None with numeric values.
    """
    results = [
        {"id": "a", "views_count": 100},
        {"id": "b", "views_count": None},
        {"id": "c", "views_count": 50},
        {"id": "d", "views_count": None},
    ]
    with pytest.raises(TypeError, match="not supported between instances"):
        sort_results(results=results, sort_by="views")


def test_sort_by_views_very_large_numbers():
    """Test sorting with views_count values greater than 2^32."""
    results = [
        {"id": "a", "views_count": 2**33},
        {"id": "b", "views_count": 2**34},
        {"id": "c", "views_count": 1000},
    ]
    sorted_results = sort_results(results=results, sort_by="views")
    
    assert [r["id"] for r in sorted_results] == ["b", "a", "c"]
    assert sorted_results[0]["views_count"] == 2**34


def test_sort_by_views_negative_numbers():
    """Test sorting with negative views_count values."""
    results = [
        {"id": "a", "views_count": 100},
        {"id": "b", "views_count": -50},
        {"id": "c", "views_count": 0},
        {"id": "d", "views_count": -100},
    ]
    sorted_results = sort_results(results=results, sort_by="views")
    
    assert [r["id"] for r in sorted_results] == ["a", "c", "b", "d"]
    assert [r["views_count"] for r in sorted_results] == [100, 0, -50, -100]


# Data Quality Edge Cases (3 tests)

def test_sort_by_invalid_sort_type():
    """Test behavior with invalid sort_by value (type checking limitation)."""
    results = [{"id": "a", "views_count": 10}]
    sorted_results = sort_results(results=results, sort_by="invalid")  # type: ignore
    
    assert len(sorted_results) == 1


def test_sort_by_views_duplicate_ids():
    """Test sorting a list with duplicate IDs but different views counts."""
    results = [
        {"id": "duplicate", "views_count": 100},
        {"id": "unique", "views_count": 500},
        {"id": "duplicate", "views_count": 200},
    ]
    sorted_results = sort_results(results=results, sort_by="views")
    
    assert sorted_results[0]["views_count"] == 500
    assert sorted_results[1]["views_count"] == 200
    assert sorted_results[2]["views_count"] == 100
    
    assert [r["id"] for r in sorted_results] == ["unique", "duplicate", "duplicate"]


def test_sort_by_views_empty_dict_items():
    """Test sorting list with items that are empty dicts (missing all fields)."""
    results = [
        {"id": "a", "views_count": 100},
        {},
        {"id": "b", "views_count": 50},
        {},
    ]
    sorted_results = sort_results(results=results, sort_by="views")
    
    assert sorted_results[0]["views_count"] == 100
    assert sorted_results[1]["views_count"] == 50
    assert sorted_results[2] == {}
    assert sorted_results[3] == {}


# ============================================================================
# IMMUTABILITY TESTS
# ============================================================================

def test_sort_by_views_does_not_mutate_original(sample_results):
    """Test that sorting by views returns new list without mutating original."""
    original_ids = [r["id"] for r in sample_results]
    original_first_id = sample_results[0]["id"]
    
    sorted_results = sort_results(sample_results, sort_by="views")
    
    assert [r["id"] for r in sample_results] == original_ids
    assert sample_results[0]["id"] == original_first_id
    
    sorted_first_id = sorted_results[0]["id"]
    assert sorted_first_id == "46fd4d15-f9bb-47c8-a8b6-d57bff7e7070"
    assert sorted_first_id != original_first_id


def test_sort_by_default_returns_same_reference(sample_results):
    """Test that default sort returns the exact same list reference."""
    sorted_results = sort_results(sample_results, sort_by="default")
    
    assert sorted_results is sample_results


# ============================================================================
# PARAMETRIZED TESTS
# ============================================================================

@pytest.mark.parametrize("sort_by,expected_first_id", [
    ("default", "0d993dea-155d-46f2-ab27-d29a7510fbcd"),
    ("views", "46fd4d15-f9bb-47c8-a8b6-d57bff7e7070"),
])
def test_sort_variations(sample_results, sort_by, expected_first_id):
    """Test different sort options return correct ordering."""
    sorted_results = sort_results(sample_results, sort_by=sort_by)
    assert sorted_results[0]["id"] == expected_first_id


@pytest.mark.parametrize("views_count,expected_position", [
    (1000000, 0),
    (50000, 2),
    (0, 6),
])
def test_sort_by_views_with_inserted_values(sample_results, views_count, expected_position):
    """Test that inserting new values maintains correct sort order."""
    new_item = {"id": "test_insert", "views_count": views_count}
    test_results = sample_results + [new_item]
    
    sorted_results = sort_results(test_results, sort_by="views")
    
    actual_position = next(
        i for i, item in enumerate(sorted_results)
        if item["id"] == "test_insert"
    )
    
    assert actual_position == expected_position
