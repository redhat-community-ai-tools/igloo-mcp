import asyncio
import re

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    """
    An example client to connect to the Igloo MCP server and test the search and fetch tools.
    """
    async with streamablehttp_client("http://localhost:8000/mcp") as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("Successfully connected to the MCP server.")

            # Step 1: Search for content
            search_tool_args = {
                "query": "test",
                "search_all": True,
                "limit": 5,
            }

            print(f"\n{'='*60}")
            print("STEP 1: SEARCH")
            print(f"{'='*60}")
            print(f"Calling the 'search' tool with arguments: {search_tool_args}")
            
            result = await session.call_tool("search", search_tool_args)
            
            if result.isError:
                print(f"Error calling search tool: {result}")
                return
            
            if not result.content or len(result.content) == 0:
                print("No search results returned.")
                return

            result_text = result.content[0].text
            
            count_match = re.search(r'Total Results Found: (\d+)', result_text)
            if count_match:
                total_results = count_match.group(1)
                print(f"\n{total_results} results received.\n")
            
            print(result_text)

            # Step 2: Extract URLs from search results
            url_pattern = r'URL: (https?://[^\s]+)'
            urls = re.findall(url_pattern, result_text)
            
            if not urls:
                print("\nNo URLs found in search results to fetch.")
                return
            
            # Limit to first 3 URLs for the demo
            urls_to_fetch = urls[:3]
            
            print(f"\n{'='*60}")
            print("STEP 2: FETCH")
            print(f"{'='*60}")
            print(f"Found {len(urls)} URLs in search results.")
            print(f"Fetching the first {len(urls_to_fetch)} pages...")
            for i, url in enumerate(urls_to_fetch, 1):
                print(f"  {i}. {url}")

            # Step 3: Fetch the pages using the fetch tool
            fetch_tool_args = {
                "url": urls_to_fetch,  # Can be single URL or list of URLs
            }

            print(f"\nCalling the 'fetch' tool with {len(urls_to_fetch)} URL(s)...")
            
            fetch_result = await session.call_tool("fetch", fetch_tool_args)
            
            if fetch_result.isError:
                print(f"Error calling fetch tool: {fetch_result}")
                return
            
            if fetch_result.content and len(fetch_result.content) > 0:
                fetch_text = fetch_result.content[0].text
                
                # Show a preview of the fetched content (first 2000 chars)
                preview_length = 2000
                if len(fetch_text) > preview_length:
                    print(f"\n--- Fetch Results (first {preview_length} chars) ---")
                    print(fetch_text[:preview_length])
                    print(f"\n... ({len(fetch_text) - preview_length} more characters)")
                else:
                    print("\n--- Fetch Results ---")
                    print(fetch_text)
            else:
                print("No content returned from fetch.")

            print(f"\n{'='*60}")
            print("Test client finished.")
            print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
