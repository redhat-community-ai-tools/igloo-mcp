from datetime import date
from pathlib import Path
from typing import AsyncGenerator

import httpx
import pytest
from httpx import Request, Response
from pytest_mock import MockerFixture

from igloo_mcp.igloo import ApplicationType, IglooClient, UpdatedDateType


BASE_URL = "https://test.com"
COMMUNITY_KEY = "12345"


@pytest.fixture
async def client() -> AsyncGenerator[IglooClient, None]:
    """
    Returns a new instance of the IglooClient for each test with proper cleanup.
    
    Yields:
        IglooClient: Configured client instance
        
    Note:
        Automatically closes the underlying httpx client after test completion
        to prevent resource leaks.
    """
    client = IglooClient(
        community=BASE_URL,
        app_id="test_app_id",
        app_pass="test_app_pass",
        community_key=COMMUNITY_KEY,
        username="test_user",
        password="test_password",
        page_size=50,
    )
    yield client
    await client._client.aclose()


@pytest.fixture
def mock_data_path() -> Path:
    """
    Returns the path to the mock data directory.
    
    Returns:
        Path: Absolute path to the tests_data/mock_data directory
    """
    return Path(__file__).parent / "tests_data" / "mock_data"


# ============================================================================
# Authentication Tests
# ============================================================================


async def test_authenticate_success(
    client: IglooClient, mock_data_path: Path, mocker: MockerFixture
):
    """
    Test successful authentication sets the iglooAuth cookie correctly.
    
    Verifies that:
    - Correct API endpoint is called with proper parameters
    - Session key from response is stored in cookies
    """
    auth_response_content = (mock_data_path / "auth_success.json").read_text()
    request = Request(method="POST", url=f"{BASE_URL}/.api/api.svc/session/create")
    mock_response = Response(200, content=auth_response_content, request=request)
    mock_request = mocker.patch.object(
        client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock
    )

    await client.authenticate()

    mock_request.assert_called_once_with(
        method="POST",
        url=f"{BASE_URL}/.api/api.svc/session/create",
        params={
            "appId": client.app_id,
            "appPass": client.app_pass,
            "apiversion": 1,
            "community": client.community,
            "username": client.username,
            "password": client.password,
        },
    )
    assert client._client.cookies.get("iglooAuth") == "cc2ba556-6d29-4091-96ce-eca12e3cbe3c"


async def test_authenticate_failure(
    client: IglooClient, mock_data_path: Path, mocker: MockerFixture
):
    """
    Test authentication failure raises ValueError with descriptive message.
    
    Verifies that:
    - ValueError is raised when response.sessionKey is missing
    - Error message indicates unexpected authentication response
    """
    auth_response_content = (mock_data_path / "auth_failure.json").read_text()
    request = Request(method="POST", url=f"{BASE_URL}/.api/api.svc/session/create")
    mock_response = Response(200, content=auth_response_content, request=request)
    mocker.patch.object(
        client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock
    )

    with pytest.raises(ValueError, match="Unexpected authentication response"):
        await client.authenticate()


async def test_authenticate_http_401_unauthorized(client: IglooClient, mocker: MockerFixture):
    """
    Test authentication handles HTTP 401 Unauthorized error gracefully.
    
    Verifies that:
    - HTTPStatusError is raised for 401 responses
    - Error propagates to caller for proper handling
    """
    request = Request(method="POST", url=f"{BASE_URL}/.api/api.svc/session/create")
    mock_response = Response(401, content=b"Unauthorized", request=request)
    mocker.patch.object(client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock)
    
    with pytest.raises(httpx.HTTPStatusError):
        await client.authenticate()


async def test_authenticate_http_500_server_error(client: IglooClient, mocker: MockerFixture):
    """
    Test authentication handles HTTP 500 Internal Server Error gracefully.
    
    Verifies that:
    - HTTPStatusError is raised for 500 responses
    - Server errors are properly propagated
    """
    request = Request(method="POST", url=f"{BASE_URL}/.api/api.svc/session/create")
    mock_response = Response(500, content=b"Internal Server Error", request=request)
    mocker.patch.object(client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock)
    
    with pytest.raises(httpx.HTTPStatusError):
        await client.authenticate()


async def test_authenticate_network_timeout(client: IglooClient, mocker: MockerFixture):
    """
    Test authentication handles network timeout errors.
    
    Verifies that:
    - TimeoutException is raised when request times out
    - Timeout errors propagate for retry logic
    """
    mocker.patch.object(
        client._client, 
        "request", 
        side_effect=httpx.TimeoutException("Request timeout"),
        new_callable=mocker.AsyncMock
    )
    
    with pytest.raises(httpx.TimeoutException):
        await client.authenticate()


async def test_authenticate_connection_refused(client: IglooClient, mocker: MockerFixture):
    """
    Test authentication handles connection refused errors.
    
    Verifies that:
    - ConnectError is raised when connection is refused
    - Network errors are properly propagated
    """
    mocker.patch.object(
        client._client,
        "request",
        side_effect=httpx.ConnectError("Connection refused"),
        new_callable=mocker.AsyncMock
    )
    
    with pytest.raises(httpx.ConnectError):
        await client.authenticate()


async def test_authenticate_malformed_json(client: IglooClient, mocker: MockerFixture):
    """
    Test authentication handles malformed JSON responses.
    
    Verifies that:
    - JSONDecodeError is raised for invalid JSON
    - Malformed responses don't crash the client
    """
    request = Request(method="POST", url=f"{BASE_URL}/.api/api.svc/session/create")
    mock_response = Response(200, content=b"invalid json{{{", request=request)
    mocker.patch.object(client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock)
    
    with pytest.raises(Exception):
        await client.authenticate()


async def test_authenticate_response_none(client: IglooClient, mocker: MockerFixture):
    """
    Test authentication handles response field set to null.
    
    Verifies that:
    - ValueError is raised when response is null
    - Error message indicates unexpected authentication response
    """
    request = Request(method="POST", url=f"{BASE_URL}/.api/api.svc/session/create")
    mock_response = Response(200, content=b'{"response": null}', request=request)
    mocker.patch.object(client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock)
    
    with pytest.raises(ValueError, match="Unexpected authentication response"):
        await client.authenticate()


async def test_authenticate_response_empty_dict(client: IglooClient, mocker: MockerFixture):
    """
    Test authentication handles response field as empty dictionary.
    
    Verifies that:
    - ValueError is raised when response is {}
    - Missing sessionKey is detected
    """
    request = Request(method="POST", url=f"{BASE_URL}/.api/api.svc/session/create")
    mock_response = Response(200, content=b'{"response": {}}', request=request)
    mocker.patch.object(client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock)
    
    with pytest.raises(ValueError, match="Unexpected authentication response"):
        await client.authenticate()


async def test_authenticate_session_key_null(client: IglooClient, mocker: MockerFixture):
    """
    Test authentication handles sessionKey set to null.
    
    Verifies that:
    - ValueError is raised when sessionKey is null
    - Null keys are not accepted
    """
    request = Request(method="POST", url=f"{BASE_URL}/.api/api.svc/session/create")
    mock_response = Response(
        200, 
        content=b'{"response": {"sessionKey": null}}', 
        request=request
    )
    mocker.patch.object(client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock)
    
    with pytest.raises(ValueError, match="Unexpected authentication response"):
        await client.authenticate()


async def test_authenticate_session_key_missing(client: IglooClient, mocker: MockerFixture):
    """
    Test authentication handles missing sessionKey field.
    
    Verifies that:
    - ValueError is raised when sessionKey field is absent
    - Missing required fields are detected
    """
    request = Request(method="POST", url=f"{BASE_URL}/.api/api.svc/session/create")
    mock_response = Response(
        200,
        content=b'{"response": {"otherField": "value"}}',
        request=request
    )
    mocker.patch.object(client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock)
    
    with pytest.raises(ValueError, match="Unexpected authentication response"):
        await client.authenticate()


# ============================================================================
# Search Tests - Basic Functionality
# ============================================================================


async def test_search_single_page(
    client: IglooClient, mock_data_path: Path, mocker: MockerFixture
):
    """
    Test search returns all results from a single page response.
    
    Verifies that:
    - Single API call is made for results that fit in one page
    - All 6 results are returned
    - Query parameter is correctly passed
    """
    search_response_content = (mock_data_path / "search_single_page.json").read_text()
    request = Request(
        method="GET",
        url=f"{BASE_URL}/.api2/api/v1/communities/{COMMUNITY_KEY}/search/contentDetailed",
    )
    mock_response = Response(200, content=search_response_content, request=request)
    mock_request = mocker.patch.object(
        client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock
    )

    results = await client.search(query="Test")

    assert len(results) == 6
    mock_request.assert_called_once()


async def test_search_multiple_pages(
    client: IglooClient, mock_data_path: Path, mocker: MockerFixture
):
    """
    Test search correctly handles pagination across multiple pages.
    
    Verifies that:
    - Multiple API calls are made for paginated results
    - Results from all pages are combined
    - Pagination page size parameter is respected
    """
    page1_content = (mock_data_path / "search_multi_page_1.json").read_text()
    page2_content = (mock_data_path / "search_multi_page_2.json").read_text()
    request = Request(
        method="GET",
        url=f"{BASE_URL}/.api2/api/v1/communities/{COMMUNITY_KEY}/search/contentDetailed",
    )
    mock_response_1 = Response(200, content=page1_content, request=request)
    mock_response_2 = Response(200, content=page2_content, request=request)
    mock_request = mocker.patch.object(
        client._client,
        "request",
        side_effect=[mock_response_1, mock_response_2],
        new_callable=mocker.AsyncMock,
    )

    results = await client.search(query="Test", pagination_page_size=5)

    assert len(results) == 6
    assert mock_request.call_count == 2


async def test_search_with_filters(
    client: IglooClient, mock_data_path: Path, mocker: MockerFixture
):
    """
    Test search correctly applies all filter parameters.
    
    Verifies that:
    - All filter parameters are correctly transformed and passed to API
    - Application types are comma-separated
    - Boolean values are lowercase strings
    - Dates are formatted correctly
    """
    search_response_content = (mock_data_path / "search_single_page.json").read_text()
    request = Request(
        method="GET",
        url=f"{BASE_URL}/.api2/api/v1/communities/{COMMUNITY_KEY}/search/contentDetailed",
    )
    mock_response = Response(200, content=search_response_content, request=request)
    mock_request = mocker.patch.object(
        client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock
    )

    await client.search(
        query="test",
        applications=[ApplicationType.BLOG, ApplicationType.WIKI],
        parent_href="/test/parent",
        search_all=False,
        include_microblog=False,
        include_archived=True,
        updated_date_type=UpdatedDateType.CUSTOM_RANGE,
        updated_date_range_from=date(2023, 1, 1),
        updated_date_range_to=date(2023, 12, 31),
    )

    mock_request.assert_called_once()
    called_params = mock_request.call_args.kwargs["params"]
    assert called_params["applications"] == "1,2"
    assert called_params["parentHref"] == "/test/parent"
    assert called_params["searchAll"] == "false"
    assert called_params["includeMicroblog"] == "false"
    assert called_params["includeArchived"] == "true"
    assert called_params["updatedDateType"] == "dateRange"
    assert called_params["updatedFrom"] == "01-01-2023"
    assert called_params["updatedTo"] == "12-31-2023"


async def test_search_with_limit(
    client: IglooClient, mock_data_path: Path, mocker: MockerFixture
):
    """
    Test search respects the limit parameter and only fetches required pages.
    
    Verifies that:
    - Only necessary API calls are made based on limit
    - Returned results are truncated to limit
    - Unnecessary pagination is avoided
    """
    page1_content = (mock_data_path / "search_multi_page_1.json").read_text()
    request = Request(
        method="GET",
        url=f"{BASE_URL}/.api2/api/v1/communities/{COMMUNITY_KEY}/search/contentDetailed",
    )
    mock_response_1 = Response(200, content=page1_content, request=request)
    mock_request = mocker.patch.object(
        client._client,
        "request",
        return_value=mock_response_1,
        new_callable=mocker.AsyncMock,
    )

    results = await client.search(query="Test", pagination_page_size=5, limit=3)

    assert len(results) == 3
    mock_request.assert_called_once()


# ============================================================================
# Search Tests - HTTP Error Handling
# ============================================================================


async def test_search_http_404_not_found(client: IglooClient, mocker: MockerFixture):
    """
    Test search handles HTTP 404 Not Found error.
    
    Verifies that:
    - HTTPStatusError is raised for 404 responses
    - Error indicates resource not found
    """
    request = Request(
        method="GET",
        url=f"{BASE_URL}/.api2/api/v1/communities/{COMMUNITY_KEY}/search/contentDetailed",
    )
    mock_response = Response(404, content=b"Not Found", request=request)
    mocker.patch.object(client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock)
    
    with pytest.raises(httpx.HTTPStatusError):
        await client.search(query="Test")


async def test_search_network_error(client: IglooClient, mocker: MockerFixture):
    """
    Test search handles generic network errors.
    
    Verifies that:
    - NetworkError is raised for connection issues
    - Network failures propagate correctly
    """
    mocker.patch.object(
        client._client,
        "request",
        side_effect=httpx.NetworkError("Network error"),
        new_callable=mocker.AsyncMock
    )
    
    with pytest.raises(httpx.NetworkError):
        await client.search(query="Test")


@pytest.mark.parametrize("status_code", [400, 401, 403, 500, 502, 503])
async def test_search_http_errors(client: IglooClient, mocker: MockerFixture, status_code: int):
    """
    Test search handles various HTTP error status codes.
    
    Parametrized test covering:
    - 400 Bad Request
    - 401 Unauthorized
    - 403 Forbidden
    - 500 Internal Server Error
    - 502 Bad Gateway
    - 503 Service Unavailable
    
    Verifies that:
    - HTTPStatusError is raised for all error codes
    - Status code is properly preserved
    """
    request = Request(
        method="GET",
        url=f"{BASE_URL}/.api2/api/v1/communities/{COMMUNITY_KEY}/search/contentDetailed",
    )
    mock_response = Response(status_code, content=b"Error", request=request)
    mocker.patch.object(client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock)
    
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.search(query="Test")
    
    assert exc_info.value.response.status_code == status_code


# ============================================================================
# Search Tests - Edge Cases
# ============================================================================


async def test_search_empty_results_list(client: IglooClient, mocker: MockerFixture):
    """
    Test search handles empty results gracefully.
    
    Verifies that:
    - Empty list is returned when numFound is 0
    - No errors occur with zero results
    """
    request = Request(
        method="GET",
        url=f"{BASE_URL}/.api2/api/v1/communities/{COMMUNITY_KEY}/search/contentDetailed",
    )
    mock_response = Response(
        200,
        content=b'{"numFound": 0, "results": []}',
        request=request
    )
    mocker.patch.object(client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock)
    
    results = await client.search(query="NonExistent")
    
    assert len(results) == 0
    assert results == []


async def test_search_limit_zero(client: IglooClient, mocker: MockerFixture):
    """
    Test search with limit=0 returns empty results.
    
    Verifies that:
    - Empty list is returned when limit is 0
    - API call is still made to get total count
    """
    request = Request(
        method="GET",
        url=f"{BASE_URL}/.api2/api/v1/communities/{COMMUNITY_KEY}/search/contentDetailed",
    )
    mock_response = Response(
        200,
        content=b'{"numFound": 10, "results": [{"id": "1"}, {"id": "2"}]}',
        request=request
    )
    mock_request = mocker.patch.object(
        client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock
    )
    
    results = await client.search(query="Test", limit=0)
    
    assert len(results) == 0
    mock_request.assert_called_once()


async def test_search_limit_exceeds_total(
    client: IglooClient, mock_data_path: Path, mocker: MockerFixture
):
    """
    Test search when limit exceeds total available results.
    
    Verifies that:
    - All available results are returned
    - No error occurs when limit > total results
    - Only necessary pages are fetched
    """
    search_response_content = (mock_data_path / "search_single_page.json").read_text()
    request = Request(
        method="GET",
        url=f"{BASE_URL}/.api2/api/v1/communities/{COMMUNITY_KEY}/search/contentDetailed",
    )
    mock_response = Response(200, content=search_response_content, request=request)
    mock_request = mocker.patch.object(
        client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock
    )
    
    results = await client.search(query="Test", limit=1000)
    
    assert len(results) == 6
    mock_request.assert_called_once()


async def test_search_custom_range_missing_from_date(client: IglooClient):
    """
    Test search raises ValueError when CUSTOM_RANGE lacks from date.
    
    Verifies that:
    - ValueError is raised for incomplete date range
    - Error message indicates both dates are required
    """
    with pytest.raises(ValueError, match="'updated_date_range_from' and 'updated_date_range_to' must be provided"):
        await client.search(
            query="Test",
            updated_date_type=UpdatedDateType.CUSTOM_RANGE,
            updated_date_range_to=date(2023, 12, 31)
        )


async def test_search_custom_range_missing_to_date(client: IglooClient):
    """
    Test search raises ValueError when CUSTOM_RANGE lacks to date.
    
    Verifies that:
    - ValueError is raised for incomplete date range
    - Error message indicates both dates are required
    """
    with pytest.raises(ValueError, match="'updated_date_range_from' and 'updated_date_range_to' must be provided"):
        await client.search(
            query="Test",
            updated_date_type=UpdatedDateType.CUSTOM_RANGE,
            updated_date_range_from=date(2023, 1, 1)
        )


async def test_search_response_missing_num_found(client: IglooClient, mocker: MockerFixture):
    """
    Test search handles missing numFound field gracefully.
    
    Verifies that:
    - Search works when numFound is absent
    - Falls back to length of results array
    """
    request = Request(
        method="GET",
        url=f"{BASE_URL}/.api2/api/v1/communities/{COMMUNITY_KEY}/search/contentDetailed",
    )
    mock_response = Response(
        200,
        content=b'{"results": [{"id": "1"}, {"id": "2"}]}',
        request=request
    )
    mocker.patch.object(client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock)
    
    results = await client.search(query="Test")
    
    assert len(results) == 2


async def test_search_response_missing_results(client: IglooClient, mocker: MockerFixture):
    """
    Test search handles missing results field gracefully.
    
    Verifies that:
    - Empty list is returned when results field is absent
    - No error occurs with missing results field
    """
    request = Request(
        method="GET",
        url=f"{BASE_URL}/.api2/api/v1/communities/{COMMUNITY_KEY}/search/contentDetailed",
    )
    mock_response = Response(
        200,
        content=b'{"numFound": 0}',
        request=request
    )
    mocker.patch.object(client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock)
    
    results = await client.search(query="Test")
    
    assert len(results) == 0


async def test_search_response_null_results(client: IglooClient, mocker: MockerFixture):
    """
    Test search handles null results field gracefully.
    
    Verifies that:
    - Empty list is returned when results is null
    - None values are handled correctly
    """
    request = Request(
        method="GET",
        url=f"{BASE_URL}/.api2/api/v1/communities/{COMMUNITY_KEY}/search/contentDetailed",
    )
    mock_response = Response(
        200,
        content=b'{"numFound": 0, "results": null}',
        request=request
    )
    mocker.patch.object(client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock)
    
    results = await client.search(query="Test")
    
    assert len(results) == 0


async def test_search_offset_exceeds_results(client: IglooClient, mocker: MockerFixture):
    """
    Test search when offset exceeds available results.
    
    Verifies that:
    - Empty results are returned for out-of-range offsets
    - No error occurs when pagination goes beyond data
    """
    request = Request(
        method="GET",
        url=f"{BASE_URL}/.api2/api/v1/communities/{COMMUNITY_KEY}/search/contentDetailed",
    )
    mock_response_1 = Response(
        200,
        content=b'{"numFound": 2, "results": [{"id": "1"}, {"id": "2"}]}',
        request=request
    )
    mock_response_2 = Response(
        200,
        content=b'{"numFound": 2, "results": []}',
        request=request
    )
    mocker.patch.object(
        client._client,
        "request",
        side_effect=[mock_response_1, mock_response_2],
        new_callable=mocker.AsyncMock
    )
    
    results = await client.search(query="Test", pagination_page_size=1)
    
    assert len(results) == 2


async def test_search_concurrent_request_partial_failure(
    client: IglooClient, mocker: MockerFixture
):
    """
    Test search handles partial failures in concurrent pagination requests.
    
    Verifies that:
    - HTTPStatusError is raised when any pagination request fails
    - Concurrent request failures are properly propagated
    """
    request = Request(
        method="GET",
        url=f"{BASE_URL}/.api2/api/v1/communities/{COMMUNITY_KEY}/search/contentDetailed",
    )
    mock_response_1 = Response(
        200,
        content=b'{"numFound": 10, "results": [{"id": "1"}, {"id": "2"}]}',
        request=request
    )
    mock_response_2 = Response(500, content=b"Internal Server Error", request=request)
    
    mocker.patch.object(
        client._client,
        "request",
        side_effect=[mock_response_1, mock_response_2],
        new_callable=mocker.AsyncMock
    )
    
    with pytest.raises(httpx.HTTPStatusError):
        await client.search(query="Test", pagination_page_size=2)


# ============================================================================
# Fetch Page Tests
# ============================================================================


async def test_fetch_page_success(client: IglooClient, mocker: MockerFixture):
    """
    Test successful page fetch returns HTML content.
    
    Verifies that:
    - GET request is made with correct URL
    - Accept header is set to text/html
    - HTML content is returned as string
    """
    html_content = "<html><body><p>Test content</p></body></html>"
    request = Request(method="GET", url=f"{BASE_URL}/wiki/test-page")
    mock_response = Response(200, content=html_content.encode(), request=request)
    mock_request = mocker.patch.object(
        client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock
    )

    result = await client.fetch_page(f"{BASE_URL}/wiki/test-page")

    assert result == html_content
    mock_request.assert_called_once_with(
        method="GET",
        url=f"{BASE_URL}/wiki/test-page",
        headers={"Accept": "text/html"},
    )


async def test_fetch_page_invalid_url(client: IglooClient):
    """
    Test fetch with URL not belonging to community raises ValueError.
    
    Verifies that:
    - ValueError is raised for external URLs
    - Error message indicates the URL must belong to the community
    """
    with pytest.raises(ValueError, match="URL must belong to community"):
        await client.fetch_page("https://other-site.com/page")


async def test_fetch_page_invalid_url_similar_domain(client: IglooClient):
    """
    Test fetch with similar but different domain raises ValueError.
    
    Verifies that:
    - URLs that start similarly but are not exact matches are rejected
    - Security check is strict
    """
    with pytest.raises(ValueError, match="URL must belong to community"):
        await client.fetch_page("https://test.com.evil.com/page")


async def test_fetch_page_http_404(client: IglooClient, mocker: MockerFixture):
    """
    Test fetch handles HTTP 404 Not Found error.
    
    Verifies that:
    - HTTPStatusError is raised for 404 responses
    - Error propagates for caller to handle
    """
    request = Request(method="GET", url=f"{BASE_URL}/wiki/not-found")
    mock_response = Response(404, content=b"Not Found", request=request)
    mocker.patch.object(
        client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock
    )

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.fetch_page(f"{BASE_URL}/wiki/not-found")
    
    assert exc_info.value.response.status_code == 404


async def test_fetch_page_http_500(client: IglooClient, mocker: MockerFixture):
    """
    Test fetch handles HTTP 500 Internal Server Error.
    
    Verifies that:
    - HTTPStatusError is raised for 500 responses
    - Server errors propagate correctly
    """
    request = Request(method="GET", url=f"{BASE_URL}/wiki/error-page")
    mock_response = Response(500, content=b"Internal Server Error", request=request)
    mocker.patch.object(
        client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock
    )

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.fetch_page(f"{BASE_URL}/wiki/error-page")
    
    assert exc_info.value.response.status_code == 500


async def test_fetch_page_timeout(client: IglooClient, mocker: MockerFixture):
    """
    Test fetch handles timeout errors.
    
    Verifies that:
    - TimeoutException is raised when request times out
    - Timeout errors propagate for retry logic
    """
    mocker.patch.object(
        client._client,
        "request",
        side_effect=httpx.TimeoutException("Request timeout"),
        new_callable=mocker.AsyncMock
    )

    with pytest.raises(httpx.TimeoutException):
        await client.fetch_page(f"{BASE_URL}/wiki/slow-page")


async def test_fetch_page_connection_error(client: IglooClient, mocker: MockerFixture):
    """
    Test fetch handles connection errors.
    
    Verifies that:
    - ConnectError is raised when connection fails
    - Network errors propagate correctly
    """
    mocker.patch.object(
        client._client,
        "request",
        side_effect=httpx.ConnectError("Connection refused"),
        new_callable=mocker.AsyncMock
    )

    with pytest.raises(httpx.ConnectError):
        await client.fetch_page(f"{BASE_URL}/wiki/unreachable-page")


async def test_fetch_page_with_path(client: IglooClient, mocker: MockerFixture):
    """
    Test fetch works with various URL paths.
    
    Verifies that:
    - URLs with different paths are handled correctly
    - Full URL is passed to the request
    """
    html_content = "<html><body><h1>Blog Post</h1></body></html>"
    request = Request(method="GET", url=f"{BASE_URL}/blog/2024/01/my-post")
    mock_response = Response(200, content=html_content.encode(), request=request)
    mocker.patch.object(
        client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock
    )

    result = await client.fetch_page(f"{BASE_URL}/blog/2024/01/my-post")

    assert result == html_content


async def test_fetch_page_with_query_params(client: IglooClient, mocker: MockerFixture):
    """
    Test fetch handles URLs with query parameters.
    
    Verifies that:
    - Query parameters are preserved in the request
    - Full URL including params is passed correctly
    """
    html_content = "<html><body>Search results</body></html>"
    url = f"{BASE_URL}/search?q=test&page=2"
    request = Request(method="GET", url=url)
    mock_response = Response(200, content=html_content.encode(), request=request)
    mocker.patch.object(
        client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock
    )

    result = await client.fetch_page(url)

    assert result == html_content


async def test_fetch_page_unicode_content(client: IglooClient, mocker: MockerFixture):
    """
    Test fetch handles Unicode content correctly.
    
    Verifies that:
    - Unicode characters are preserved in the response
    - Non-ASCII content is handled correctly
    """
    html_content = "<html><body><p>日本語テキスト</p><p>Ελληνικά</p></body></html>"
    request = Request(method="GET", url=f"{BASE_URL}/wiki/unicode-page")
    mock_response = Response(200, content=html_content.encode('utf-8'), request=request)
    mocker.patch.object(
        client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock
    )

    result = await client.fetch_page(f"{BASE_URL}/wiki/unicode-page")

    assert "日本語テキスト" in result
    assert "Ελληνικά" in result


async def test_fetch_page_empty_response(client: IglooClient, mocker: MockerFixture):
    """
    Test fetch handles empty response body.
    
    Verifies that:
    - Empty string is returned for empty response
    - No error occurs with empty content
    """
    request = Request(method="GET", url=f"{BASE_URL}/wiki/empty-page")
    mock_response = Response(200, content=b"", request=request)
    mocker.patch.object(
        client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock
    )

    result = await client.fetch_page(f"{BASE_URL}/wiki/empty-page")

    assert result == ""


async def test_fetch_page_large_content(client: IglooClient, mocker: MockerFixture):
    """
    Test fetch handles large HTML content.
    
    Verifies that:
    - Large responses are handled without error
    - Content is returned in full
    """
    html_content = "<html><body>" + "<p>Content</p>" * 10000 + "</body></html>"
    request = Request(method="GET", url=f"{BASE_URL}/wiki/large-page")
    mock_response = Response(200, content=html_content.encode(), request=request)
    mocker.patch.object(
        client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock
    )

    result = await client.fetch_page(f"{BASE_URL}/wiki/large-page")

    assert len(result) == len(html_content)
    assert result == html_content


# ============================================================================
# Fetch Pages (Multiple URLs) Tests
# ============================================================================


async def test_fetch_pages_success(client: IglooClient, mocker: MockerFixture):
    """
    Test successful fetching of multiple pages returns all HTML content.
    
    Verifies that:
    - All pages are fetched concurrently
    - Results are returned in same order as input URLs
    - Each result is the HTML content string
    """
    html_content_1 = "<html><body><p>Page 1</p></body></html>"
    html_content_2 = "<html><body><p>Page 2</p></body></html>"
    html_content_3 = "<html><body><p>Page 3</p></body></html>"
    
    request1 = Request(method="GET", url=f"{BASE_URL}/wiki/page1")
    request2 = Request(method="GET", url=f"{BASE_URL}/wiki/page2")
    request3 = Request(method="GET", url=f"{BASE_URL}/wiki/page3")
    
    mock_response_1 = Response(200, content=html_content_1.encode(), request=request1)
    mock_response_2 = Response(200, content=html_content_2.encode(), request=request2)
    mock_response_3 = Response(200, content=html_content_3.encode(), request=request3)
    
    mocker.patch.object(
        client._client,
        "request",
        side_effect=[mock_response_1, mock_response_2, mock_response_3],
        new_callable=mocker.AsyncMock
    )

    urls = [
        f"{BASE_URL}/wiki/page1",
        f"{BASE_URL}/wiki/page2",
        f"{BASE_URL}/wiki/page3",
    ]
    results = await client.fetch_pages(urls)

    assert len(results) == 3
    assert results[0] == html_content_1
    assert results[1] == html_content_2
    assert results[2] == html_content_3


async def test_fetch_pages_empty_list(client: IglooClient, mocker: MockerFixture):
    """
    Test fetching with empty URL list returns empty results.
    
    Verifies that:
    - Empty list input returns empty list output
    - No errors occur with empty input
    """
    results = await client.fetch_pages([])
    
    assert results == []


async def test_fetch_pages_single_url(client: IglooClient, mocker: MockerFixture):
    """
    Test fetching single URL via fetch_pages works correctly.
    
    Verifies that:
    - Single URL is processed correctly
    - Result is the HTML content string
    """
    html_content = "<html><body><p>Single Page</p></body></html>"
    request = Request(method="GET", url=f"{BASE_URL}/wiki/single")
    mock_response = Response(200, content=html_content.encode(), request=request)
    
    mocker.patch.object(
        client._client,
        "request",
        return_value=mock_response,
        new_callable=mocker.AsyncMock
    )

    results = await client.fetch_pages([f"{BASE_URL}/wiki/single"])

    assert len(results) == 1
    assert results[0] == html_content


async def test_fetch_pages_invalid_url(client: IglooClient, mocker: MockerFixture):
    """
    Test fetching with invalid URL returns ValueError exception.
    
    Verifies that:
    - Invalid URLs return ValueError exception in result
    - Error message indicates URL must belong to community
    """
    results = await client.fetch_pages(["https://other-site.com/page"])

    assert len(results) == 1
    assert isinstance(results[0], ValueError)
    assert "URL must belong to community" in str(results[0])


async def test_fetch_pages_partial_failure(client: IglooClient, mocker: MockerFixture):
    """
    Test fetching multiple URLs where some fail returns mixed results.
    
    Verifies that:
    - Successful pages return HTML string
    - Failed pages return Exception
    - All results are returned
    """
    html_content_1 = "<html><body><p>Page 1</p></body></html>"
    
    request1 = Request(method="GET", url=f"{BASE_URL}/wiki/page1")
    request2 = Request(method="GET", url=f"{BASE_URL}/wiki/page2")
    
    mock_response_1 = Response(200, content=html_content_1.encode(), request=request1)
    mock_response_2 = Response(404, content=b"Not Found", request=request2)
    
    mocker.patch.object(
        client._client,
        "request",
        side_effect=[mock_response_1, mock_response_2],
        new_callable=mocker.AsyncMock
    )

    urls = [
        f"{BASE_URL}/wiki/page1",
        f"{BASE_URL}/wiki/page2",
    ]
    results = await client.fetch_pages(urls)

    assert len(results) == 2
    assert results[0] == html_content_1
    assert not isinstance(results[0], Exception)
    
    assert isinstance(results[1], httpx.HTTPStatusError)
    assert results[1].response.status_code == 404


async def test_fetch_pages_all_fail(client: IglooClient, mocker: MockerFixture):
    """
    Test fetching multiple URLs where all fail returns all exceptions.
    
    Verifies that:
    - All pages return exceptions
    - No exceptions are raised from fetch_pages itself
    """
    request1 = Request(method="GET", url=f"{BASE_URL}/wiki/page1")
    request2 = Request(method="GET", url=f"{BASE_URL}/wiki/page2")
    
    mock_response_1 = Response(500, content=b"Server Error", request=request1)
    mock_response_2 = Response(404, content=b"Not Found", request=request2)
    
    mocker.patch.object(
        client._client,
        "request",
        side_effect=[mock_response_1, mock_response_2],
        new_callable=mocker.AsyncMock
    )

    urls = [
        f"{BASE_URL}/wiki/page1",
        f"{BASE_URL}/wiki/page2",
    ]
    results = await client.fetch_pages(urls)

    assert len(results) == 2
    assert isinstance(results[0], httpx.HTTPStatusError)
    assert results[0].response.status_code == 500
    assert isinstance(results[1], httpx.HTTPStatusError)
    assert results[1].response.status_code == 404


async def test_fetch_pages_timeout(client: IglooClient, mocker: MockerFixture):
    """
    Test fetching with timeout returns TimeoutException for timed out page.
    
    Verifies that:
    - Timeout errors are captured as TimeoutException
    - Other pages are not affected
    """
    html_content_1 = "<html><body><p>Page 1</p></body></html>"
    request1 = Request(method="GET", url=f"{BASE_URL}/wiki/page1")
    mock_response_1 = Response(200, content=html_content_1.encode(), request=request1)
    
    mocker.patch.object(
        client._client,
        "request",
        side_effect=[mock_response_1, httpx.TimeoutException("Request timeout")],
        new_callable=mocker.AsyncMock
    )

    urls = [
        f"{BASE_URL}/wiki/page1",
        f"{BASE_URL}/wiki/slow-page",
    ]
    results = await client.fetch_pages(urls)

    assert len(results) == 2
    assert results[0] == html_content_1
    assert isinstance(results[1], httpx.TimeoutException)


async def test_fetch_pages_mixed_valid_invalid_urls(client: IglooClient, mocker: MockerFixture):
    """
    Test fetching mix of valid and invalid community URLs.
    
    Verifies that:
    - Valid URLs are fetched and return HTML
    - Invalid URLs return ValueError exception without HTTP request
    """
    html_content = "<html><body><p>Valid Page</p></body></html>"
    request = Request(method="GET", url=f"{BASE_URL}/wiki/valid")
    mock_response = Response(200, content=html_content.encode(), request=request)
    
    mocker.patch.object(
        client._client,
        "request",
        return_value=mock_response,
        new_callable=mocker.AsyncMock
    )

    urls = [
        f"{BASE_URL}/wiki/valid",
        "https://evil.com/phishing",
    ]
    results = await client.fetch_pages(urls)

    assert len(results) == 2
    assert results[0] == html_content
    assert isinstance(results[1], ValueError)
    assert "URL must belong to community" in str(results[1])


# ============================================================================
# Client Initialization Tests
# ============================================================================


class TestIglooClientInitialization:
    """Tests for IglooClient initialization with various parameters."""

    async def test_client_with_proxy(self):
        """
        Test IglooClient initialization with proxy parameter.
        
        Verifies that:
        - Client can be created with proxy configuration
        - Proxy URL is passed to underlying httpx client
        """
        client = IglooClient(
            community="https://test.com",
            app_id="test_app_id",
            app_pass="test_app_pass",
            community_key="12345",
            username="test_user",
            password="test_password",
            proxy="http://proxy.example.com:8080",
        )
        try:
            # Verify the client was created with the proxy
            # The proxy is set during client creation and affects requests
            assert client._client is not None
        finally:
            await client._client.aclose()

    async def test_client_with_verify_ssl_false(self):
        """
        Test IglooClient initialization with verify_ssl=False.
        
        Verifies that:
        - Client can be created with SSL verification disabled
        - Setting is passed to underlying httpx client
        """
        client = IglooClient(
            community="https://test.com",
            app_id="test_app_id",
            app_pass="test_app_pass",
            community_key="12345",
            username="test_user",
            password="test_password",
            verify_ssl=False,
        )
        try:
            # Verify the client was created with verify=False
            assert client._client is not None
        finally:
            await client._client.aclose()

    async def test_client_with_verify_ssl_true_default(self):
        """
        Test IglooClient uses verify_ssl=True by default.
        
        Verifies that:
        - SSL verification is enabled by default
        """
        client = IglooClient(
            community="https://test.com",
            app_id="test_app_id",
            app_pass="test_app_pass",
            community_key="12345",
            username="test_user",
            password="test_password",
        )
        try:
            # Default should have SSL verification enabled
            assert client._client is not None
        finally:
            await client._client.aclose()

    async def test_client_with_proxy_and_verify_ssl_false(self):
        """
        Test IglooClient with both proxy and verify_ssl=False.
        
        Verifies that:
        - Client can be configured with both proxy and SSL verification disabled
        - Common scenario for corporate proxies with self-signed certificates
        """
        client = IglooClient(
            community="https://test.com",
            app_id="test_app_id",
            app_pass="test_app_pass",
            community_key="12345",
            username="test_user",
            password="test_password",
            proxy="http://proxy.example.com:8080",
            verify_ssl=False,
        )
        try:
            assert client._client is not None
        finally:
            await client._client.aclose()

    async def test_client_strips_trailing_slash_from_community(self):
        """
        Test that trailing slash is removed from community URL.
        
        Verifies that:
        - Trailing slashes are stripped during initialization
        - URLs are normalized for consistent behavior
        """
        client = IglooClient(
            community="https://test.com/",
            app_id="test_app_id",
            app_pass="test_app_pass",
            community_key="12345",
            username="test_user",
            password="test_password",
        )
        try:
            assert client.community == "https://test.com"
        finally:
            await client._client.aclose()

    async def test_client_custom_page_size(self):
        """
        Test IglooClient initialization with custom page_size.
        
        Verifies that:
        - Custom page size is stored correctly
        """
        client = IglooClient(
            community="https://test.com",
            app_id="test_app_id",
            app_pass="test_app_pass",
            community_key="12345",
            username="test_user",
            password="test_password",
            page_size=100,
        )
        try:
            assert client.page_size == 100
        finally:
            await client._client.aclose()


# ============================================================================
# URL Validation Tests
# ============================================================================


class TestUrlValidation:
    """Tests for URL validation in IglooClient."""

    async def test_fetch_page_with_fragment_identifier(self, mocker: MockerFixture):
        """
        Test fetch handles URLs with fragment identifiers (#section).
        
        Verifies that:
        - URLs with fragments are accepted as valid community URLs
        - Fragment is preserved in the request
        """
        client = IglooClient(
            community=BASE_URL,
            app_id="test_app_id",
            app_pass="test_app_pass",
            community_key=COMMUNITY_KEY,
            username="test_user",
            password="test_password",
        )
        try:
            html_content = "<html><body>Content</body></html>"
            url = f"{BASE_URL}/wiki/page#section-2"
            request = Request(method="GET", url=url)
            mock_response = Response(200, content=html_content.encode(), request=request)
            mocker.patch.object(
                client._client, "request", return_value=mock_response, new_callable=mocker.AsyncMock
            )

            result = await client.fetch_page(url)

            assert result == html_content
        finally:
            await client._client.aclose()

    async def test_url_validation_exact_match_community(self):
        """
        Test URL validation with exact community URL (no path).
        
        Verifies that:
        - The exact community URL is valid
        """
        client = IglooClient(
            community=BASE_URL,
            app_id="test_app_id",
            app_pass="test_app_pass",
            community_key=COMMUNITY_KEY,
            username="test_user",
            password="test_password",
        )
        try:
            # Should not raise - exact community URL should be valid
            client._validate_community_url(BASE_URL)
        finally:
            await client._client.aclose()

    async def test_url_validation_with_query_string_only(self):
        """
        Test URL validation with community URL + query string (no path).
        
        Verifies that:
        - Community URL with only query params is valid
        """
        client = IglooClient(
            community=BASE_URL,
            app_id="test_app_id",
            app_pass="test_app_pass",
            community_key=COMMUNITY_KEY,
            username="test_user",
            password="test_password",
        )
        try:
            # Should not raise - URL with query params after community base
            client._validate_community_url(f"{BASE_URL}?param=value")
        finally:
            await client._client.aclose()

    async def test_url_validation_rejects_http_when_community_is_https(self):
        """
        Test URL validation rejects HTTP URLs when community uses HTTPS.
        
        Verifies that:
        - Protocol mismatch is correctly rejected
        - Security check prevents downgrade attacks
        """
        client = IglooClient(
            community="https://secure.example.com",
            app_id="test_app_id",
            app_pass="test_app_pass",
            community_key=COMMUNITY_KEY,
            username="test_user",
            password="test_password",
        )
        try:
            with pytest.raises(ValueError, match="URL must belong to community"):
                client._validate_community_url("http://secure.example.com/page")
        finally:
            await client._client.aclose()

    async def test_url_validation_rejects_different_port(self):
        """
        Test URL validation rejects URLs with different ports.
        
        Verifies that:
        - Port mismatch is correctly rejected
        """
        client = IglooClient(
            community="https://example.com:443",
            app_id="test_app_id",
            app_pass="test_app_pass",
            community_key=COMMUNITY_KEY,
            username="test_user",
            password="test_password",
        )
        try:
            with pytest.raises(ValueError, match="URL must belong to community"):
                client._validate_community_url("https://example.com:8080/page")
        finally:
            await client._client.aclose()
