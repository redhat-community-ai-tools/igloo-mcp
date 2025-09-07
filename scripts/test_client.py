import asyncio
import re

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    """
    An example client to connect to the Igloo MCP server and call the search tool.
    """
    async with streamablehttp_client("http://localhost:8000/mcp") as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("Successfully connected to the MCP server.")

            search_tool_args = {
                "query": "test",
                "search_all": True,
                "limit": 5,
            }

            print(f"Calling the 'search' tool with arguments: {search_tool_args}")
            result = await session.call_tool("search", search_tool_args)
            
            if result.isError:
                print(f"Error calling tool: {result}")
                return
            
            if result.content and len(result.content) > 0:
                result_text = result.content[0].text
                
                count_match = re.search(r'Total Results Found: (\d+)', result_text)
                if count_match:
                    total_results = count_match.group(1)
                    print(f"\n{total_results} results received.\n")
                
                print(result_text)
            else:
                print("No results returned.")

            print("\nTest client finished.")


if __name__ == "__main__":
    asyncio.run(main())
