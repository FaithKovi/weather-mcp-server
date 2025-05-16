
import os
import json
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
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

app = FastAPI()

# Pydantic models for requests
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

async def fetch_alerts(lat, lon):
    async with aiohttp.ClientSession() as session:
        params = {'lat': lat, 'lon': lon, 'exclude': 'current,minutely,hourly,daily', 'appid': OPENWEATHER_API_KEY}
        async with session.get('https://api.openweathermap.org/data/2.5/onecall', params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                logger.error(f"Alerts fetch error: {text}")
                raise HTTPException(status_code=resp.status, detail=text)
            return await resp.json()

# Endpoints (MCP Tools exposed as HTTP APIs)

@app.post("/get_current_weather")
async def get_current_weather(req: WeatherRequest):
    data = await fetch_weather(req.location)
    return {
        'location': f"{data['name']}, {data['sys']['country']}",
        'temperature': f"{data['main']['temp']}°C",
        'feels_like': f"{data['main']['feels_like']}°C",
        'humidity': f"{data['main']['humidity']}%",
        'wind_speed': f"{data['wind']['speed']} m/s",
        'conditions': data['weather'][0]['description'],
        'timestamp': data['dt']
    }

@app.post("/get_weather_alerts")
async def get_weather_alerts(req: WeatherRequest):
    data = await fetch_weather(req.location)
    lat, lon = data['coord']['lat'], data['coord']['lon']
    alerts_data = await fetch_alerts(lat, lon)
    alerts = alerts_data.get('alerts', [])
    if not alerts:
        return {'location': req.location, 'alerts': [], 'status': 'No active alerts'}

    formatted = [{
        'event': alert['event'],
        'description': alert['description'],
        'start': alert['start'],
        'end': alert['end']
    } for alert in alerts]

    return {'location': req.location, 'alerts': formatted, 'status': f"{len(alerts)} alerts found"}

# Run locally for testing
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3050)
