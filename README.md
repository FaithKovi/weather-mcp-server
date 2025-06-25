# Weather MCP Server (SSE-based)

A working OpenWeather API-based Model Context Protocol (MCP) server that provides weather tools via Server-Sent Events (SSE) transport. This server is fully compatible with Cline and other MCP clients.

## Features

- **Current Weather**: Get real-time weather data for any location
- **5-Day Forecast**: Get detailed weather forecasts  
- **Coordinates Weather**: Get weather data using latitude/longitude coordinates
- **SSE Transport**: Uses Server-Sent Events for real-time communication
- **MCP Compliant**: Fully compatible with the Model Context Protocol specification

## Available Tools

1. **`get_current_weather`**
   - Description: Get current weather information for a specified location
   - Parameters:
     - `location` (string, required): City name, "city,country" format
     - `units` (string, optional): "metric", "imperial", or "kelvin" (default: "metric")

2. **`get_weather_forecast`**
   - Description: Get 5-day weather forecast for a specified location
   - Parameters:
     - `location` (string, required): City name, "city,country" format  
     - `units` (string, optional): "metric", "imperial", or "kelvin" (default: "metric")

3. **`get_weather_by_coordinates`**
   - Description: Get current weather information for specific coordinates
   - Parameters:
     - `latitude` (number, required): Latitude of the location
     - `longitude` (number, required): Longitude of the location
     - `units` (string, optional): "metric", "imperial", or "kelvin" (default: "metric")

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file with your OpenWeather API key:

```env
OPENWEATHER_API_KEY=your_openweather_api_key_here
PORT=3051
```

Get your free API key from [OpenWeatherMap](https://openweathermap.org/api).

### 3. Run the Server

```bash
python main.py
```

The server will start on `http://0.0.0.0:3051` with the SSE endpoint at `http://0.0.0.0:3051/sse`.

Example output:
```
Starting OpenWeather MCP Server on 0.0.0.0:3051
SSE endpoint: http://0.0.0.0:3051/sse
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:3051 (Press CTRL+C to quit)
```

### 4. Test the Server

Run the test client to verify everything works:

```bash
python test_client.py http://localhost:3051/sse
```

## Integration with Cline

This server is designed to work seamlessly with Cline. Add the following to your MCP settings:

```json
{
  "weather-openweather": {
    "autoApprove": [
      "get_current_weather",
      "get_weather_forecast", 
      "get_weather_by_coordinates"
    ],
    "disabled": false,
    "timeout": 30,
    "type": "sse",
    "url": "http://localhost:3051/sse"
  }
}
```

## Usage Examples

### Current Weather
```
Query: "What's the weather like in London?"
Response: 🌤️ Weather for London, GB
Temperature: 15.2°C (feels like 14.8°C)
Conditions: Scattered Clouds
Humidity: 72%
Wind: 3.1 m/s at 250°
```

### Weather Forecast  
```
Query: "Give me the 5-day forecast for Tokyo"
Response: 🔮 5-Day Forecast for Tokyo, JP
[Detailed 5-day forecast with temperatures and conditions]
```

### Weather by Coordinates
```
Query: "What's the weather at coordinates 40.7128, -74.0060?"
Response: Weather data for New York City coordinates
```

## Technical Details

- **Framework**: Built with FastMCP and Starlette
- **Transport**: Server-Sent Events (SSE) for real-time communication
- **API**: OpenWeatherMap API for weather data
- **Protocol**: Model Context Protocol (MCP) 2024-11-05
- **ASGI**: Properly configured ASGI application with correct SSE handling

## Architecture

The server follows the SSE-based MCP pattern:

1. **FastMCP**: Handles tool registration and MCP protocol implementation
2. **SseServerTransport**: Manages SSE connections and message routing
3. **Starlette**: Provides the ASGI web framework
4. **Uvicorn**: ASGI server for production deployment

## Key Differences from STDIO

Unlike STDIO-based MCP servers that run as subprocesses, this SSE-based server:

- Runs as an independent HTTP service
- Supports multiple concurrent client connections
- Can be deployed to cloud platforms (Heroku, Railway, etc.)
- Allows clients to connect/disconnect dynamically
- Better fits cloud-native and microservice architectures
- Enables web-based MCP clients

## Deployment

### Local Development
```bash
python main.py --host 0.0.0.0 --port 3051
```

### Production Deployment
The server includes a `Procfile` for easy deployment to platforms like Heroku:
```
web: python main.py --host 0.0.0.0 --port $PORT
```

## Files

- `main.py` - Main MCP server implementation with weather tools
- `test_client.py` - Test client for server verification
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (API keys)
- `Procfile` - Deployment configuration
- `README.md` - This documentation

## Troubleshooting

### Server Not Starting
- **Missing API Key**: Check that `OPENWEATHER_API_KEY` is set in `.env`
- **Port in Use**: Ensure port 3051 is not already in use
- **Dependencies**: Verify all requirements are installed: `pip install -r requirements.txt`

### ASGI/SSE Errors
- **TypeError 'NoneType'**: The server has been fixed to properly handle SSE responses
- **ASGI Protocol Errors**: Server now correctly implements the ASGI SSE pattern
- **Connection Issues**: Restart the server if you encounter connection problems

### Tools Not Working  
- **API Key Invalid**: Confirm the OpenWeather API key is valid and has quota remaining
- **Network Issues**: Check connectivity to `api.openweathermap.org`
- **Location Not Found**: Try different location formats (e.g., "London,UK" instead of "London")

### Cline Integration Issues
- **Server Not Found**: Ensure the server is running on the correct port (3051)
- **MCP Settings**: Restart Cline after updating MCP server settings
- **URL Format**: Verify the SSE endpoint URL is `http://localhost:3051/sse`

### Common Error Messages
- `"Missing OpenWeather API key"`: Add your API key to the `.env` file
- `"Unable to fetch weather data"`: Check location spelling and API key validity
- `"HTTP 404: Could not find session"`: Ensure the server is running before connecting

## Recent Updates

- Fixed ASGI application SSE response handling
- Improved error handling and user feedback
- Enhanced weather data formatting with emojis
- Updated troubleshooting guide with common issues

## License

This project is based on the MCP reference implementations and follows the same patterns for SSE-based servers. It demonstrates best practices for building production-ready MCP servers with SSE transport.
