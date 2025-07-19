"""
IP Camera function for capturing and sending snapshots.
"""

import httpx
import base64
import logging
from typing import Dict, Any
from io import BytesIO

from functions.base import FunctionBase, bot_function
from core.config import settings

logger = logging.getLogger(__name__)


@bot_function("ip_camera")
class IPCameraFunction(FunctionBase):
    """Capture and send IP camera snapshots."""
    
    def __init__(self):
        """Initialize the IP camera function."""
        super().__init__(
            name="ip_camera",
            description="Capture and send IP camera snapshots",
            parameters={
                "camera_name": {
                    "type": "string",
                    "description": "Name of the camera (optional, for identification)",
                    "required": False
                },
                "camera_url": {
                    "type": "string",
                    "description": "Camera snapshot URL (overrides default)",
                    "required": False
                },
                "format": {
                    "type": "string",
                    "description": "Response format (base64, url, or description)",
                    "default": "description"
                }
            },
            command_info={
                "usage": "!ip_camera [nombre]",
                "examples": [
                    "!ip_camera",
                    "!ip_camera sala"
                ],
                "parameter_mapping": {
                    "camera_name": "first_arg"  # First argument as camera name
                }
            }
        )
        self.default_camera_url = settings.IP_CAMERA_URL
        self.camera_username = settings.IP_CAMERA_USERNAME
        self.camera_password = settings.IP_CAMERA_PASSWORD
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the IP camera function.
        
        Args:
            **kwargs: Function parameters
            
        Returns:
            Camera snapshot result
        """
        try:
            # Validate parameters
            params = self.validate_parameters(**kwargs)
            camera_name = params.get("camera_name", "IP Camera")
            camera_url = params.get("camera_url", self.default_camera_url)
            format_type = params.get("format", "description")
            
            if not camera_url:
                return self.format_error_response(
                    "Camera URL must be configured or provided"
                )
            
            logger.info(f"Capturing snapshot from {camera_name}")
            
            # Capture snapshot
            snapshot_result = await self._capture_snapshot(camera_url)
            
            if not snapshot_result.get("success"):
                return self.format_error_response(snapshot_result.get("error", "Failed to capture snapshot"))
            
            # Format response based on requested format
            if format_type == "base64":
                response_message = f"📸 Snapshot captured from {camera_name} (base64 encoded)"
                result_data = {
                    "camera_name": camera_name,
                    "image_base64": snapshot_result["image_base64"],
                    "image_size": snapshot_result.get("size", 0),
                    "timestamp": snapshot_result.get("timestamp")
                }
            elif format_type == "url":
                response_message = f"📸 Snapshot captured from {camera_name}\\nURL: {camera_url}"
                result_data = {
                    "camera_name": camera_name,
                    "camera_url": camera_url,
                    "timestamp": snapshot_result.get("timestamp")
                }
            else:  # description
                response_message = f"📸 Snapshot successfully captured from {camera_name}!"
                if snapshot_result.get("size"):
                    size_kb = snapshot_result["size"] / 1024
                    response_message += f"\\nImage size: {size_kb:.1f} KB"
                
                result_data = {
                    "camera_name": camera_name,
                    "image_size": snapshot_result.get("size", 0),
                    "timestamp": snapshot_result.get("timestamp")
                }
            
            return self.format_success_response(result_data, response_message)
            
        except Exception as e:
            logger.error(f"Error in IP camera function: {str(e)}")
            return self.format_error_response(str(e))
    
    async def _capture_snapshot(self, camera_url: str) -> Dict[str, Any]:
        """Capture a snapshot from the camera."""
        try:
            # Prepare authentication
            auth = None
            if self.camera_username and self.camera_password:
                auth = (self.camera_username, self.camera_password)
            
            # Capture snapshot
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(camera_url, auth=auth)
                response.raise_for_status()
                
                # Check if response is an image
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    return {
                        "success": False,
                        "error": f"Response is not an image: {content_type}"
                    }
                
                # Get image data
                image_data = response.content
                image_base64 = base64.b64encode(image_data).decode("utf-8")
                
                return {
                    "success": True,
                    "image_base64": image_base64,
                    "size": len(image_data),
                    "content_type": content_type,
                    "timestamp": response.headers.get("date")
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error capturing snapshot: {e}")
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: Failed to access camera"
            }
        except httpx.TimeoutException:
            logger.error("Timeout capturing snapshot")
            return {
                "success": False,
                "error": "Camera request timed out"
            }
        except Exception as e:
            logger.error(f"Error capturing snapshot: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_camera_response(self, result: Dict[str, Any]) -> str:
        """Format camera response message."""
        try:
            camera_name = result.get("camera_name", "IP Camera")
            timestamp = result.get("timestamp")
            size = result.get("size", 0)
            
            response = f"📸 Snapshot captured from {camera_name}\\n"
            
            if size > 0:
                size_kb = size / 1024
                response += f"Size: {size_kb:.1f} KB\\n"
            
            if timestamp:
                response += f"Timestamp: {timestamp}\\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting camera response: {str(e)}")
            return f"📸 Camera snapshot captured successfully!"
