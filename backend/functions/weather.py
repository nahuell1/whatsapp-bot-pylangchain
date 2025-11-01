"""Weather function using OpenMeteo API.

Provides current weather and forecast information for any location.
"""

import logging
from typing import Any, Dict, Optional

import httpx

from functions.base import FunctionBase, bot_function

logger = logging.getLogger(__name__)


FORECAST_DAYS_MIN = 1
FORECAST_DAYS_MAX = 7
DEFAULT_FORECAST_DAYS = 1
DEFAULT_UNITS = "celsius"


@bot_function("weather")
class WeatherFunction(FunctionBase):
    """Get weather information for a location using OpenMeteo API.
    
    Provides current weather conditions and multi-day forecasts with
    temperature, precipitation, and weather conditions.
    """
    
    def __init__(self):
        """Initialize the weather function with API endpoints and parameters."""
        super().__init__(
            name="weather",
            description="Get current weather and forecast for a location",
            parameters={
                "location": {
                    "type": "string",
                    "description": "Location to get weather for (city name or coordinates)",
                    "required": True
                },
                "days": {
                    "type": "integer",
                    "description": f"Number of forecast days ({FORECAST_DAYS_MIN}-{FORECAST_DAYS_MAX})",
                    "default": DEFAULT_FORECAST_DAYS
                },
                "units": {
                    "type": "string",
                    "description": "Temperature units (celsius or fahrenheit)",
                    "default": DEFAULT_UNITS
                }
            },
            command_info={
                "usage": "!weather <ubicación>",
                "examples": [
                    "!weather Don Torcuato",
                    "!weather Buenos Aires",
                    "!weather Madrid"
                ],
                "parameter_mapping": {
                    "location": "join_args"  # Join all arguments as location
                }
            },
            intent_examples=[
                {
                    "message": "what's the weather in Madrid",
                    "parameters": {"location": "Madrid"}
                },
                {
                    "message": "weather forecast for Buenos Aires", 
                    "parameters": {"location": "Buenos Aires", "days": 3}
                }
            ]
        )
        self.geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        self.weather_url = "https://api.open-meteo.com/v1/forecast"
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the weather function.
        
        Args:
            **kwargs: Function parameters (location, days, units)
            
        Returns:
            Dict containing weather data and formatted message
        """
        try:
            params = self.validate_parameters(**kwargs)
            location = params["location"]
            days = params.get("days", DEFAULT_FORECAST_DAYS)
            units = params.get("units", DEFAULT_UNITS)
            
            logger.info("Getting weather for %s", location)
            
            coordinates = await self._get_coordinates(location)
            if not coordinates:
                return self.format_error_response(
                    f"Could not find location: {location}"
                )
            
            weather_data = await self._get_weather_data(
                coordinates, days, units
            )
            if not weather_data:
                return self.format_error_response("Failed to get weather data")
            
            response_message = self._format_weather_response(
                weather_data, location
            )
            
            return self.format_success_response(weather_data, response_message)
            
        except Exception as e:
            logger.error("Error in weather function: %s", str(e))
            return self.format_error_response(str(e))
    
    async def _get_coordinates(self, location: str) -> Dict[str, Any]:
        """Get geographic coordinates for a location name.
        
        Args:
            location: Location name (city, address, etc.)
            
        Returns:
            Dict with latitude, longitude, name, and country or empty dict
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.geocoding_url,
                    params={
                        "name": location,
                        "count": 1,
                        "language": "en",
                        "format": "json"
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                if data.get("results"):
                    result = data["results"][0]
                    return {
                        "latitude": result["latitude"],
                        "longitude": result["longitude"],
                        "name": result["name"],
                        "country": result.get("country", "")
                    }
                return {}
        except Exception as e:
            logger.error("Error getting coordinates: %s", str(e))
            return {}
    
    async def _get_weather_data(
        self,
        coordinates: Dict[str, Any],
        days: int,
        units: str
    ) -> Dict[str, Any]:
        """Get weather data for geographic coordinates.
        
        Args:
            coordinates: Dict with latitude and longitude
            days: Number of forecast days
            units: Temperature units (celsius or fahrenheit)
            
        Returns:
            Dict with weather data or empty dict on error
        """
        try:
            temp_unit = "celsius" if units == "celsius" else "fahrenheit"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.weather_url,
                    params={
                        "latitude": coordinates["latitude"],
                        "longitude": coordinates["longitude"],
                        "current_weather": True,
                        "daily": (
                            "weathercode,temperature_2m_max,temperature_2m_min,"
                            "precipitation_sum,windspeed_10m_max"
                        ),
                        "forecast_days": days,
                        "temperature_unit": temp_unit,
                        "timezone": "auto"
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                data["location"] = coordinates
                
                return data
                
        except Exception as e:
            logger.error("Error getting weather data: %s", str(e))
            return {}
    
    def _format_weather_response(
        self,
        weather_data: Dict[str, Any],
        location: str
    ) -> str:
        """Format weather data into a human-readable message.
        
        Args:
            weather_data: Weather data from OpenMeteo API
            location: Original location query
            
        Returns:
            Formatted weather message with current conditions and forecast
        """
        try:
            current = weather_data.get("current_weather", {})
            daily = weather_data.get("daily", {})
            location_info = weather_data.get("location", {})
            
            weather_codes = self._get_weather_code_mapping()
            
            current_temp = current.get("temperature", 0)
            current_code = current.get("weathercode", 0)
            current_condition = weather_codes.get(current_code, "Unknown")
            
            temp_unit = (
                "C" if weather_data.get(
                    "current_weather_units", {}
                ).get("temperature") == "°C" else "F"
            )
            
            response = (
                f"🌍 Weather for {location_info.get('name', location)}\n\n"
                f"🌡️ Current: {current_temp}°{temp_unit}\n"
                f"{current_condition}\n"
            )
            
            if daily and daily.get("time"):
                response += "\n📅 Forecast:\n"
                max_days = min(3, len(daily["time"]))
                for i in range(max_days):
                    if i < len(daily.get("temperature_2m_max", [])):
                        date = daily["time"][i]
                        max_temp = daily["temperature_2m_max"][i]
                        min_temp = daily["temperature_2m_min"][i]
                        precipitation = (
                            daily.get("precipitation_sum", [0])[i]
                            if i < len(daily.get("precipitation_sum", []))
                            else 0
                        )
                        
                        response += f"• {date}: {min_temp}°-{max_temp}°"
                        if precipitation > 0:
                            response += f", 🌧️ {precipitation}mm"
                        response += "\n"
            
            return response
            
        except Exception as e:
            logger.error("Error formatting weather response: %s", str(e))
            return (
                f"Weather data received for {location}, "
                "but formatting failed."
            )
    
    @staticmethod
    def _get_weather_code_mapping() -> Dict[int, str]:
        """Get WMO weather code to emoji/description mapping.
        
        Returns:
            Dict mapping weather codes to human-readable descriptions
        """
        return {
            0: "☀️ Clear sky",
            1: "🌤️ Mainly clear",
            2: "⛅ Partly cloudy",
            3: "☁️ Overcast",
            45: "🌫️ Foggy",
            48: "🌫️ Depositing rime fog",
            51: "🌦️ Light drizzle",
            53: "🌦️ Moderate drizzle",
            55: "🌦️ Dense drizzle",
            61: "🌧️ Slight rain",
            63: "🌧️ Moderate rain",
            65: "🌧️ Heavy rain",
            80: "🌦️ Slight rain showers",
            81: "🌦️ Moderate rain showers",
            82: "🌦️ Violent rain showers",
            95: "⛈️ Thunderstorm",
            96: "⛈️ Thunderstorm with slight hail",
            99: "⛈️ Thunderstorm with heavy hail"
        }
