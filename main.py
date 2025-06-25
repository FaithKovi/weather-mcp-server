import os
import argparse
from typing import Any
import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import StreamingResponse
from starlette.routing import Mount, Route
from mcp.server.sse import SseServerTransport
from mcp.server import Server
import uvicorn

# Load environment variables
load_dotenv()

# Initialize FastMCP server for Weather tools (SSE)
mcp = FastMCP("weather-openweather")

# Constants
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
if not OPENWEATHER_API_KEY:
    raise ValueError("Missing OpenWeather API key. Set OPENWEATHER_API_KEY in .env file.")

OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
USER_AGENT = "weather-mcp-server/1.0"


async def make_openweather_request(endpoint: str, params: dict) -> dict[str, Any] | None:
    """Make a request to the OpenWeather API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
    }
    
    # Add API key to params
    params["appid"] = OPENWEATHER_API_KEY
    
    url = f"{OPENWEATHER_BASE_URL}/{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            print(f"Request error: {e}")
            return None


def format_weather_data(data: dict, units: str = "metric") -> str:
    """Format weather data into a readable string."""
    try:
        location = f"{data['name']}, {data['sys']['country']}"
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        wind_speed = data['wind'].get('speed', 0)
        wind_dir = data['wind'].get('deg', 0)
        conditions = data['weather'][0]['description'].title()
        
        # Set temperature unit based on API units parameter
        if units == "metric":
            temp_unit = "C"
        elif units == "imperial":
            temp_unit = "F"
        else:
            temp_unit = "K"
        
        return f"""🌤️ Weather for {location}
Temperature: {temp:.1f}°{temp_unit} (feels like {feels_like:.1f}°{temp_unit})
Conditions: {conditions}
Humidity: {humidity}%
Wind: {wind_speed} m/s at {wind_dir}°
"""
    except KeyError as e:
        return f"Error formatting weather data: missing field {e}"


def format_forecast_data(data: dict, units: str = "metric") -> str:
    """Format forecast data into a readable string."""
    try:
        city_info = data['city']
        location = f"{city_info['name']}, {city_info['country']}"
        
        # Set temperature unit based on API units parameter
        if units == "metric":
            temp_unit = "C"
        elif units == "imperial":
            temp_unit = "F"
        else:
            temp_unit = "K"
        
        forecast_text = f"🔮 5-Day Forecast for {location}\n\n"
        
        # Group forecasts by date
        daily_forecasts = {}
        for item in data['list'][:15]:  # Limit to 15 items (about 5 days)
            date = item['dt_txt'].split(' ')[0]
            if date not in daily_forecasts:
                daily_forecasts[date] = []
            daily_forecasts[date].append(item)
        
        for date, forecasts in daily_forecasts.items():
            forecast_text += f"📅 {date}:\n"
            for forecast in forecasts[:3]:  # Show first 3 forecasts per day
                time = forecast['dt_txt'].split(' ')[1][:5]  # HH:MM
                temp = forecast['main']['temp']
                conditions = forecast['weather'][0]['description'].title()
                forecast_text += f"  {time}: {temp:.1f}°{temp_unit} - {conditions}\n"
            forecast_text += "\n"
        
        return forecast_text
    except KeyError as e:
        return f"Error formatting forecast data: missing field {e}"


@mcp.tool()
async def get_current_weather(location: str, units: str = "metric") -> str:
    """Get current weather information for a specified location.

    Args:
        location: The location to get weather for (city name, city,country, etc.)
        units: Temperature units (metric, imperial, or kelvin). Default is metric.
    """
    params = {
        'q': location,
        'units': units
    }
    
    data = await make_openweather_request('weather', params)
    
    if not data:
        return f"Unable to fetch weather data for '{location}'. Please check the location name and try again."
    
    return format_weather_data(data, units)


@mcp.tool()
async def get_weather_forecast(location: str, units: str = "metric") -> str:
    """Get 5-day weather forecast for a specified location.

    Args:
        location: The location to get forecast for (city name, city,country, etc.)
        units: Temperature units (metric, imperial, or kelvin). Default is metric.
    """
    params = {
        'q': location,
        'units': units
    }
    
    data = await make_openweather_request('forecast', params)
    
    if not data:
        return f"Unable to fetch forecast data for '{location}'. Please check the location name and try again."
    
    return format_forecast_data(data, units)


@mcp.tool()
async def get_weather_by_coordinates(latitude: float, longitude: float, units: str = "metric") -> str:
    """Get current weather information for specific coordinates.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
        units: Temperature units (metric, imperial, or kelvin). Default is metric.
    """
    params = {
        'lat': latitude,
        'lon': longitude,
        'units': units
    }
    
    data = await make_openweather_request('weather', params)
    
    if not data:
        return f"Unable to fetch weather data for coordinates ({latitude}, {longitude})."
    
    return format_weather_data(data, units)


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


if __name__ == "__main__":
    mcp_server = mcp._mcp_server  # noqa: WPS437

    parser = argparse.ArgumentParser(description='Run OpenWeather MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=int(os.getenv('PORT', 3051)), help='Port to listen on')
    args = parser.parse_args()

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)

    print(f"Starting OpenWeather MCP Server on {args.host}:{args.port}")
    print(f"SSE endpoint: http://{args.host}:{args.port}/sse")
    
    uvicorn.run(starlette_app, host=args.host, port=args.port)
