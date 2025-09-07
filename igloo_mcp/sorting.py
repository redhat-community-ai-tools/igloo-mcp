from typing import Any, Callable, Literal


SortType = Literal["default", "views"]


def sort_results(
    results: list[dict[str, Any]], sort_by: SortType
) -> list[dict[str, Any]]:
    """
    Sorts a list of results (dicts) based on a specified criterion.

    Args:
        results (list[dict[str, Any]]): The list of search result items to sort.
        sort_by (SortType): The criterion to sort by.
            "default": No sorting is applied; the original order is returned.
            "views": Sorts the results by the 'views_count' field in descending order.

    Returns:
        list[dict[str, Any]]: The sorted list of search results.
    """
    if sort_by == "default":
        return results

    sort_key: Callable[[dict[str, Any]], Any] | None = None
    reverse = False

    if sort_by == "views":
        sort_key = _sort_by_views_key_func
        reverse = True

    return sorted(results, key=sort_key, reverse=reverse)

def _sort_by_views_key_func(item: dict[str, Any]) -> int:
    return item.get("views_count", 0)
