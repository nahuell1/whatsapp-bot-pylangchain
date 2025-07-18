"""
Home Assistant integration function.
"""

import httpx
import logging
from typing import Dict, Any

from functions.base import FunctionBase
from core.config import settings

logger = logging.getLogger(__name__)


class HomeAssistantFunction(FunctionBase):
    """Trigger Home Assistant automations and control entities."""
    
    def __init__(self):
        """Initialize the Home Assistant function."""
        super().__init__(
            name="home_assistant",
            description="Control Home Assistant entities and trigger automations",
            parameters={
                "action": {
                    "type": "string",
                    "description": "Action to perform (turn_on, turn_off, toggle, trigger_automation, get_state)",
                    "required": True
                },
                "entity_id": {
                    "type": "string",
                    "description": "Entity ID (e.g., light.living_room, automation.goodnight)",
                    "required": False
                },
                "service": {
                    "type": "string",
                    "description": "Home Assistant service to call (e.g., light.turn_on, automation.trigger)",
                    "required": False
                },
                "data": {
                    "type": "object",
                    "description": "Additional data to send with the service call",
                    "required": False
                }
            },
            command_info={
                "usage": "!home_assistant <acción> [entidad]",
                "examples": [
                    "!home_assistant turn_on light.living_room",
                    "!home_assistant turn_off lights",
                    "!home_assistant get_state sensor.temperature"
                ],
                "parameter_mapping": {
                    "action": "first_arg",  # First argument as action
                    "entity_id": "second_arg"  # Second argument as entity_id
                }
            }
        )
        self.base_url = settings.HOME_ASSISTANT_URL
        self.token = settings.HOME_ASSISTANT_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the Home Assistant function.
        
        Args:
            **kwargs: Function parameters
            
        Returns:
            Home Assistant operation result
        """
        try:
            # Check configuration
            if not self.base_url or not self.token:
                return self.format_error_response(
                    "Home Assistant URL and token must be configured"
                )
            
            # Validate parameters
            params = self.validate_parameters(**kwargs)
            action = params["action"]
            entity_id = params.get("entity_id")
            service = params.get("service")
            data = params.get("data", {})
            
            logger.info(f"Executing Home Assistant action: {action}")
            
            # Execute action
            if action == "turn_on":
                result = await self._call_service("homeassistant/turn_on", {"entity_id": entity_id})
            elif action == "turn_off":
                result = await self._call_service("homeassistant/turn_off", {"entity_id": entity_id})
            elif action == "toggle":
                result = await self._call_service("homeassistant/toggle", {"entity_id": entity_id})
            elif action == "trigger_automation":
                result = await self._call_service("automation/trigger", {"entity_id": entity_id})
            elif action == "get_state":
                result = await self._get_state(entity_id)
            elif action == "custom_service" and service:
                result = await self._call_service(service, data)
            else:
                return self.format_error_response(f"Unknown action: {action}")
            
            if result.get("success"):
                response_message = self._format_ha_response(action, entity_id, result)
                return self.format_success_response(result, response_message)
            else:
                return self.format_error_response(result.get("error", "Unknown error"))
                
        except Exception as e:
            logger.error(f"Error in Home Assistant function: {str(e)}")
            return self.format_error_response(str(e))
    
    async def _call_service(self, service: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call a Home Assistant service."""
        try:
            url = f"{self.base_url}/api/services/{service}"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=self.headers)
                response.raise_for_status()
                
                return {
                    "success": True,
                    "service": service,
                    "data": data,
                    "response": response.json() if response.content else {}
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling service {service}: {e}")
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            logger.error(f"Error calling service {service}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_state(self, entity_id: str) -> Dict[str, Any]:
        """Get the state of an entity."""
        try:
            url = f"{self.base_url}/api/states/{entity_id}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                state_data = response.json()
                return {
                    "success": True,
                    "entity_id": entity_id,
                    "state": state_data.get("state"),
                    "attributes": state_data.get("attributes", {}),
                    "last_changed": state_data.get("last_changed"),
                    "last_updated": state_data.get("last_updated")
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting state for {entity_id}: {e}")
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            logger.error(f"Error getting state for {entity_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_ha_response(self, action: str, entity_id: str, result: Dict[str, Any]) -> str:
        """Format Home Assistant response."""
        try:
            if action == "get_state":
                state = result.get("state")
                attributes = result.get("attributes", {})
                friendly_name = attributes.get("friendly_name", entity_id)
                
                response = f"🏠 {friendly_name}\n"
                response += f"State: {state}\n"
                
                # Add relevant attributes
                if "temperature" in attributes:
                    response += f"🌡️ Temperature: {attributes['temperature']}°C\n"
                if "brightness" in attributes:
                    brightness_percent = int((attributes["brightness"] / 255) * 100)
                    response += f"💡 Brightness: {brightness_percent}%\n"
                if "current_power_w" in attributes:
                    response += f"⚡ Power: {attributes['current_power_w']}W\n"
                    
                return response
            else:
                entity_name = entity_id.split(".")[-1].replace("_", " ").title()
                action_past = {
                    "turn_on": "turned on",
                    "turn_off": "turned off",
                    "toggle": "toggled",
                    "trigger_automation": "triggered"
                }.get(action, f"executed {action}")
                
                return f"🏠 {entity_name} has been {action_past} successfully!"
                
        except Exception as e:
            logger.error(f"Error formatting HA response: {str(e)}")
            return f"Home Assistant action completed: {action}"
