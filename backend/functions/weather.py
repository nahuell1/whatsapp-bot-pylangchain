"""
Weather function using OpenMeteo API.
"""

import httpx
import logging
from typing import Dict, Any

from functions.base import FunctionBase

logger = logging.getLogger(__name__)


class WeatherFunction(FunctionBase):
    """Get weather information for a location."""
    
    def __init__(self):
        """Initialize the weather function."""
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
                    "description": "Number of forecast days (1-7)",
                    "default": 1
                },
                "units": {
                    "type": "string",
                    "description": "Temperature units (celsius or fahrenheit)",
                    "default": "celsius"
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
            }
        )
        self.geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        self.weather_url = "https://api.open-meteo.com/v1/forecast"
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the weather function.
        
        Args:
            **kwargs: Function parameters
            
        Returns:
            Weather information
        """
        try:
            # Validate parameters
            params = self.validate_parameters(**kwargs)
            location = params["location"]
            days = params.get("days", 1)
            units = params.get("units", "celsius")
            
            logger.info(f"Getting weather for {location}")
            
            # Get coordinates for location
            coordinates = await self._get_coordinates(location)
            if not coordinates:
                return self.format_error_response(f"Could not find location: {location}")
            
            # Get weather data
            weather_data = await self._get_weather_data(coordinates, days, units)
            if not weather_data:
                return self.format_error_response("Failed to get weather data")
            
            # Format response
            response_message = self._format_weather_response(weather_data, location)
            
            return self.format_success_response(weather_data, response_message)
            
        except Exception as e:
            logger.error(f"Error in weather function: {str(e)}")
            return self.format_error_response(str(e))
    
    async def _get_coordinates(self, location: str) -> Dict[str, float]:
        """Get coordinates for a location."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.geocoding_url,
                    params={"name": location, "count": 1, "language": "en", "format": "json"}
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
            logger.error(f"Error getting coordinates: {str(e)}")
            return {}
    
    async def _get_weather_data(self, coordinates: Dict[str, float], days: int, units: str) -> Dict[str, Any]:
        """Get weather data for coordinates."""
        try:
            temp_unit = "celsius" if units == "celsius" else "fahrenheit"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.weather_url,
                    params={
                        "latitude": coordinates["latitude"],
                        "longitude": coordinates["longitude"],
                        "current_weather": True,
                        "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
                        "forecast_days": days,
                        "temperature_unit": temp_unit,
                        "timezone": "auto"
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Add location info
                data["location"] = coordinates
                
                return data
                
        except Exception as e:
            logger.error(f"Error getting weather data: {str(e)}")
            return {}
    
    def _format_weather_response(self, weather_data: Dict[str, Any], location: str) -> str:
        """Format weather data into a readable response."""
        try:
            current = weather_data.get("current_weather", {})
            daily = weather_data.get("daily", {})
            location_info = weather_data.get("location", {})
            
            # Weather codes mapping
            weather_codes = {
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
            
            # Current weather
            current_temp = current.get("temperature", 0)
            current_code = current.get("weathercode", 0)
            current_condition = weather_codes.get(current_code, "Unknown")
            
            response = f"🌍 Weather for {location_info.get('name', location)}\n\n"
            response += f"🌡️ Current: {current_temp}°{'C' if weather_data.get('current_weather_units', {}).get('temperature') == '°C' else 'F'}\n"
            response += f"{current_condition}\n"
            
            # Daily forecast
            if daily and len(daily.get("time", [])) > 0:
                response += "\n📅 Forecast:\n"
                for i, date in enumerate(daily.get("time", [])[:3]):  # Show max 3 days
                    if i < len(daily.get("temperature_2m_max", [])):
                        max_temp = daily["temperature_2m_max"][i]
                        min_temp = daily["temperature_2m_min"][i]
                        precipitation = daily.get("precipitation_sum", [0])[i] if i < len(daily.get("precipitation_sum", [])) else 0
                        
                        response += f"• {date}: {min_temp}°-{max_temp}°"
                        if precipitation > 0:
                            response += f", 🌧️ {precipitation}mm"
                        response += "\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting weather response: {str(e)}")
            return f"Weather data received for {location}, but formatting failed."
