import os
import json
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import aiohttp
import uvicorn

# Load .env
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Key
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
if not OPENWEATHER_API_KEY:
    logger.error("Missing OpenWeather API key. Set it in .env.")
    exit(1)

app = FastAPI(title="Weather MCP Server", version="1.0.0")

# MCP Protocol Models
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str
    params: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

class MCPTool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

class MCPToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]

# Legacy Pydantic models for direct API access
class WeatherRequest(BaseModel):
    location: str

# Utils
async def fetch_weather(location):
    async with aiohttp.ClientSession() as session:
        params = {'q': location, 'appid': OPENWEATHER_API_KEY, 'units': 'metric'}
        async with session.get('https://api.openweathermap.org/data/2.5/weather', params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                logger.error(f"Weather fetch error: {text}")
                raise HTTPException(status_code=resp.status, detail=text)
            return await resp.json()



# MCP Tool Implementations
async def get_current_weather_tool(location: str):
    """Get current weather for a location"""
    data = await fetch_weather(location)
    return {
        'location': f"{data['name']}, {data['sys']['country']}",
        'temperature': f"{data['main']['temp']}°C",
        'feels_like': f"{data['main']['feels_like']}°C",
        'humidity': f"{data['main']['humidity']}%",
        'wind_speed': f"{data['wind']['speed']} m/s",
        'conditions': data['weather'][0]['description'],
        'timestamp': data['dt']
    }



# MCP Tools Registry
MCP_TOOLS = {
    "get_current_weather": {
        "name": "get_current_weather",
        "description": "Get current weather information for a specified location",
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The location to get weather for (city, country)"
                }
            },
            "required": ["location"]
        },
        "handler": get_current_weather_tool
    }
}

# MCP Protocol Endpoints

@app.post("/mcp")
async def mcp_handler(request: MCPRequest):
    """Main MCP protocol handler"""
    try:
        if request.method == "tools/list":
            tools = [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "inputSchema": tool["inputSchema"]
                }
                for tool in MCP_TOOLS.values()
            ]
            return MCPResponse(
                id=request.id,
                result={"tools": tools}
            )
        
        elif request.method == "tools/call":
            if not request.params:
                return MCPResponse(
                    id=request.id,
                    error={"code": -32602, "message": "Invalid params"}
                )
            
            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {})
            
            if tool_name not in MCP_TOOLS:
                return MCPResponse(
                    id=request.id,
                    error={"code": -32601, "message": f"Tool '{tool_name}' not found"}
                )
            
            try:
                handler = MCP_TOOLS[tool_name]["handler"]
                result = await handler(**arguments)
                return MCPResponse(
                    id=request.id,
                    result={
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                )
            except Exception as e:
                logger.error(f"Tool execution error: {str(e)}")
                return MCPResponse(
                    id=request.id,
                    error={"code": -32603, "message": f"Tool execution failed: {str(e)}"}
                )
        
        else:
            return MCPResponse(
                id=request.id,
                error={"code": -32601, "message": f"Method '{request.method}' not found"}
            )
    
    except Exception as e:
        logger.error(f"MCP handler error: {str(e)}")
        return MCPResponse(
            id=request.id,
            error={"code": -32603, "message": "Internal error"}
        )

# MCP Info endpoint for testing
@app.get("/mcp/info")
async def mcp_info():
    """Get MCP server information"""
    return {
        "name": "Weather MCP Server",
        "version": "1.0.0",
        "tools": list(MCP_TOOLS.keys()),
        "protocol": "mcp/1.0",
        "endpoints": {
            "mcp": "/mcp",
            "info": "/mcp/info",
            "test": "/mcp/test"
        }
    }

# Test endpoint for easy MCP client testing
@app.get("/mcp/test")
async def mcp_test():
    """Test endpoint to verify MCP functionality"""
    # Test tools/list
    list_request = MCPRequest(method="tools/list", id="test-1")
    list_response = await mcp_handler(list_request)
    
    # Test tools/call with sample data
    call_request = MCPRequest(
        method="tools/call",
        id="test-2",
        params={
            "name": "get_current_weather",
            "arguments": {"location": "London, UK"}
        }
    )
    call_response = await mcp_handler(call_request)
    
    return {
        "tools_list": list_response.dict(),
        "sample_call": call_response.dict(),
        "status": "MCP server is working correctly"
    }

# Legacy HTTP endpoints (keeping for backward compatibility)
@app.post("/get_current_weather")
async def get_current_weather(req: WeatherRequest):
    """Legacy endpoint for direct HTTP access"""
    return await get_current_weather_tool(req.location)

# Easy browser testing endpoint
@app.get("/weather/{location}")
async def get_weather_by_url(location: str):
    """Get weather via URL parameter for easy browser testing"""
    return await get_current_weather_tool(location)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Weather MCP Server"}

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Weather MCP Server",
        "version": "1.0.0",
        "endpoints": {
            "mcp_protocol": "/mcp",
            "mcp_info": "/mcp/info",
            "mcp_test": "/mcp/test",
            "legacy_weather": "/get_current_weather",
            "browser_weather": "/weather/{location}",
            "health": "/health"
        }
    }

# Run locally for testing
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3050)