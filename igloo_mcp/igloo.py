import asyncio
from datetime import date
from enum import Enum
from typing import Any, Literal

import httpx


API_DATE_FORMAT = r"%m-%d-%Y"

class ApplicationType(Enum):
    BLOG = 1
    WIKI = 2
    DOCUMENT = 3
    FORUM = 4
    GALLERY = 5
    CALENDAR = 6
    PAGES = 7
    PEOPLE = 8
    SPACE = 9
    MICROBLOG = 10


class UpdatedDateType(Enum):
    PAST_HOUR = "pastHour"
    PAST_24_HOURS = "pastTwentyFourHours"
    PAST_WEEK = "pastWeek"
    PAST_MONTH = "pastMonth"
    PAST_YEAR = "pastYear"
    CUSTOM_RANGE = "dateRange"


class IglooClient:
    def __init__(
        self,
        community: str,
        community_key: str,
        app_id: str,
        app_pass: str,
        username: str,
        password: str,
        proxy: str | None = None,
        verify_ssl: bool = True,
        page_size: int = 50,
    ):
        """
        Initialize the Igloo client.

        Args:
            community (str): The base URL of the workplace community. Example: "https://iglooe.mysite.com"
            community_key (str): The numeric identifier for your digital workplace. Should be a number (e.g. "10").
            app_id (str): The application ID.
            app_pass (str): The application password.
            username (str): The username to authenticate with.
            password (str): The password to authenticate with.
            proxy (str, optional): The proxy URL to use for requests. Defaults to None.
            verify_ssl (bool, optional): Whether to verify SSL certificates. Defaults to True.
            page_size (int): The number of results to fetch per page for paginated results. Defaults to 50.
        """
        self.community = community.rstrip("/")
        self.app_id = app_id
        self.app_pass = app_pass
        self.community_key = community_key
        self.username = username
        self.password = password
        self.page_size = page_size

        self._client = httpx.AsyncClient(
            headers={
                "Accept": "application/json",
            },
            proxy=proxy,
            verify=verify_ssl,
        )

    async def _request(
        self, method: Literal["GET", "POST", "PUT", "DELETE"], endpoint: str, **kwargs
    ) -> httpx.Response:
        """
        Make a request to the Igloo API.

        Args:
            method: The HTTP method to use.
            endpoint: The endpoint to request. Must start with a slash (/).
            **kwargs: Additional arguments to pass to the request.
        """
        if method not in {"GET", "POST", "PUT", "DELETE"}:
            raise ValueError(f"Invalid HTTP method: {method}")

        response = await self._client.request(
            method=method,
            url=self.community + endpoint,
            **kwargs,
        )

        return response.raise_for_status()

    async def authenticate(self) -> None:
        """
        Authenticate with the Igloo API to obtain a session key and set it as a cookie.
        """
        response = await self._request(
            method="POST",
            endpoint="/.api/api.svc/session/create",
            params={
                "appId": self.app_id,
                "appPass": self.app_pass,
                "apiversion": 1,
                "community": self.community,
                "username": self.username,
                "password": self.password,
            },
        )

        response_data: dict[str, Any] = response.json()

        if api_key := (response_data.get("response") or {}).get("sessionKey"):
            self._client.cookies.set("iglooAuth", api_key)

        else:
            raise ValueError(
                "Unexpected authentication response:\n" + str(response_data)
            )

    async def search(
        self,
        query: str | None = None,
        applications: list[ApplicationType] | None = None,
        parent_href: str | None = None,
        search_all: bool = True,
        include_microblog: bool = True,
        include_archived: bool = False,
        updated_date_type: UpdatedDateType | None = None,
        updated_date_range_from: date | None = None,
        updated_date_range_to: date | None = None,
        pagination_page_size: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for content.

        Args:
            query (str, optional): The search query to use.
            applications (list[ApplicationType], optional): List of applications to search in (OR search).
            parent_href (str, optional): Relative path of Parent to search
            search_all (bool, optional): Whether search results should contain all keywords from the query (True)
                or any keywords from the query (False). Defaults to True.
            include_microblog (bool, optional): Whether to include microblog content in the search results. Defaults to True.
            include_archived (bool, optional): Whether to include archived content in the search results. Defaults to False.
            updated_date_type (UpdatedDateType, optional): Filter results based on when they were last updated.
            updated_date_range_from (date, optional): Start date for custom date range filter.
                Used and required only if 'updated_date_type' is 'CUSTOM_RANGE'.
            updated_date_range_to (date, optional): End date for custom date range filter.
                Used and required only if 'updated_date_type' is 'CUSTOM_RANGE'.
            pagination_page_size (int, optional): Number of results to fetch per page. Overrides the client 'page_size' client setting if provided.
                Defaults to None.
            limit (int, optional): The maximum number of results to fetch. Defaults to None (fetch all).
        
        Returns:
            list[dict]: A list of search result items.

        Notes:
            - Default boolean values are based on Igloo's API defaults.
            - `objectSearchType` filter is skipped as it did not work in testing.
        """
        page_size = pagination_page_size or self.page_size

        params: dict[str, Any] = {"limit": str(page_size)}

        if query:
            params["query"] = query

        if applications:
            params["applications"] = ",".join(str(app.value) for app in applications)

        if parent_href:
            params["parentHref"] = parent_href.rstrip("/")

        params["searchAll"] = str(search_all).lower()
        params["includeMicroblog"] = str(include_microblog).lower()
        params["includeArchived"] = str(include_archived).lower()

        if updated_date_type:
            params["updatedDateType"] = updated_date_type.value

            if updated_date_type == UpdatedDateType.CUSTOM_RANGE:
                if not (updated_date_range_from and updated_date_range_to):
                    raise ValueError(
                        "'updated_date_range_from' and 'updated_date_range_to' must be provided "
                        "when 'updated_date_type' is 'CUSTOM_RANGE'."
                    )

                params["updatedFrom"] = updated_date_range_from.strftime(API_DATE_FORMAT)
                params["updatedTo"] = updated_date_range_to.strftime(API_DATE_FORMAT)

        endpoint = (
            f"/.api2/api/v1/communities/{self.community_key}/search/contentDetailed"
        )
        first_response = await self._request(
            method="GET",
            endpoint=endpoint,
            params=params,
        )

        first_response_json = first_response.json()
        results = first_response_json.get("results") or []
        total_results_found = first_response_json.get("numFound", len(results))

        if limit is not None and limit == 0:
            return []

        if limit is not None and len(results) >= limit:
            return results[:limit]

        results_to_fetch = (
            min(limit, total_results_found)
            if limit is not None else total_results_found
        )

        tasks = []
        for offset in range(len(results), results_to_fetch, page_size):
            page_params = params.copy()
            page_params["offset"] = str(offset)

            task = self._request(
                method="GET",
                endpoint=endpoint,
                params=page_params,
            )
            tasks.append(task)

        if tasks:
            remaining_responses = await asyncio.gather(*tasks)

            for response in remaining_responses:
                response_json = response.json()
                results.extend(response_json.get("results", []))

        if limit is not None:
            return results[:limit]
        
        return results
