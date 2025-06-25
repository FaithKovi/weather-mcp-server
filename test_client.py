import asyncio
import sys
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client

class MCPTestClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_sse_server(self, server_url: str):
        """Connect to an MCP server running with SSE transport"""
        # Store the context managers so they stay alive
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        # Initialize
        await self.session.initialize()

        # List available tools to verify connection
        print("Initialized SSE client...")
        print("Listing tools...")
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])
        return tools

    async def cleanup(self):
        """Properly clean up the session and streams"""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def test_weather_tool(self, location: str = "London"):
        """Test the get_current_weather tool"""
        print(f"\nTesting get_current_weather tool with location: {location}")
        
        try:
            result = await self.session.call_tool("get_current_weather", {
                "location": location,
                "units": "metric"
            })
            print("Weather result:")
            print(result.content[0].text if result.content else "No content returned")
        except Exception as e:
            print(f"Error calling weather tool: {e}")

    async def test_forecast_tool(self, location: str = "London"):
        """Test the get_weather_forecast tool"""
        print(f"\nTesting get_weather_forecast tool with location: {location}")
        
        try:
            result = await self.session.call_tool("get_weather_forecast", {
                "location": location,
                "units": "metric"
            })
            print("Forecast result:")
            print(result.content[0].text if result.content else "No content returned")
        except Exception as e:
            print(f"Error calling forecast tool: {e}")

    async def test_coordinates_tool(self, lat: float = 51.5074, lon: float = -0.1278):
        """Test the get_weather_by_coordinates tool"""
        print(f"\nTesting get_weather_by_coordinates tool with coordinates: {lat}, {lon}")
        
        try:
            result = await self.session.call_tool("get_weather_by_coordinates", {
                "latitude": lat,
                "longitude": lon,
                "units": "metric"
            })
            print("Coordinates weather result:")
            print(result.content[0].text if result.content else "No content returned")
        except Exception as e:
            print(f"Error calling coordinates tool: {e}")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_client.py <URL of SSE MCP server (i.e. http://localhost:3051/sse)>")
        sys.exit(1)

    client = MCPTestClient()
    try:
        tools = await client.connect_to_sse_server(server_url=sys.argv[1])
        
        # Test each available tool
        await client.test_weather_tool("New York")
        await client.test_forecast_tool("Paris")
        await client.test_coordinates_tool(40.7128, -74.0060)  # New York coordinates
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
