"""All Cameras function to capture snapshots from all configured cameras.

Captures snapshots from multiple cameras concurrently with semaphore-based
rate limiting to prevent system overload.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from functions.base import bot_function
from functions.camera import CameraFunction

logger = logging.getLogger(__name__)

MAX_CONCURRENT_CAPTURES = 3


@bot_function("allcameras")
class AllCamerasFunction(CameraFunction):
    """Capture snapshots from all configured IP cameras concurrently.
    
    Extends CameraFunction to capture from multiple cameras simultaneously
    with rate limiting via semaphore.
    """
    
    def __init__(self):
        """Initialize the all cameras function with parent camera discovery."""
        super().__init__()
        
        self.name = "allcameras"
        self.description = "Capture snapshots from all configured IP cameras"
        self.parameters = {}
        self.command_info = {
            "usage": "!allcameras",
            "examples": [
                "!allcameras"
            ],
            "parameter_mapping": {},
            "aliases": ["allcams", "cameras"]
        }
        self.intent_examples = [
            {
                "message": "show me all cameras",
                "parameters": {}
            },
            {
                "message": "take pictures from all cameras",
                "parameters": {}
            }
        ]
        
        logger.info(
            "AllCameras function initialized with %d cameras",
            len(self.cameras)
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the all cameras function.
        
        Args:
            **kwargs: Function parameters (none required)
            
        Returns:
            Dict with results from all camera captures
        """
        try:
            if not self.cameras:
                return self.format_error_response(
                    "No cameras configured in the system"
                )
            
            camera_names = list(self.cameras.keys())
            logger.info(
                "Starting capture from %d cameras: %s",
                len(camera_names),
                camera_names
            )
            
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_CAPTURES)
            
            async def capture_with_semaphore(camera_name: str):
                async with semaphore:
                    return await self._capture_single_camera(camera_name)
            
            tasks = [capture_with_semaphore(name) for name in camera_names]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_captures = []
            failed_captures = []
            
            for i, result in enumerate(results):
                camera_name = camera_names[i]
                
                if isinstance(result, Exception):
                    failed_captures.append({
                        "camera_name": camera_name,
                        "error": str(result)
                    })
                    logger.error("Camera %s failed: %s", camera_name, str(result))
                elif result and result.get('success'):
                    successful_captures.append(result)
                    logger.info("Camera %s captured successfully", camera_name)
                else:
                    failed_captures.append({
                        "camera_name": camera_name,
                        "error": "Unknown capture failure"
                    })
                    logger.warning(
                        "Camera %s failed with unknown error", camera_name
                    )
            
            total_cameras = len(camera_names)
            success_count = len(successful_captures)
            failed_count = len(failed_captures)
            
            if success_count == 0:
                return self.format_error_response(
                    f"Could not capture image from any of the "
                    f"{total_cameras} cameras"
                )
            
            timestamp = datetime.now()
            response_text = (
                f"📸 **Multiple Camera Capture**\n\n"
                f"✅ Successful: {success_count}\n"
                f"❌ Failed: {failed_count}\n"
                f"📱 Total: {total_cameras}\n\n"
            )
            
            if successful_captures:
                response_text += "**Captured cameras:**\n"
                for capture in successful_captures:
                    camera_name = capture['camera_name']
                    camera_type = capture['camera_type'].upper()
                    response_text += f"• {camera_name} ({camera_type})\n"
            
            if failed_captures:
                response_text += "\n**Failed cameras:**\n"
                for failure in failed_captures:
                    response_text += f"• {failure['camera_name']}\n"
            
            response_text += (
                f"\n🕐 Completed: {timestamp.strftime('%d/%m/%Y %H:%M:%S')}"
            )
            
            return self.format_success_response(
                {
                    "total_cameras": total_cameras,
                    "successful_captures": successful_captures,
                    "failed_captures": failed_captures,
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "timestamp": timestamp.isoformat()
                },
                response_text
            )
            
        except Exception as e:
            logger.error("Error in all cameras function: %s", str(e))
            return self.format_error_response(
                f"Error capturing images: {str(e)}"
            )
    
    async def _capture_single_camera(self, camera_name: str) -> Dict[str, Any]:
        """Capture snapshot from a single camera.
        
        Args:
            camera_name: Name of the camera to capture from
            
        Returns:
            Dict with capture result and metadata
        """
        try:
            camera_config = self.cameras[camera_name]
            
            logger.info("Capturing from camera: %s", camera_name)
            snapshot_data = await self._capture_snapshot(
                camera_name, camera_config
            )
            
            if snapshot_data:
                return {
                    "success": True,
                    "camera_name": camera_name,
                    "camera_type": camera_config['TYPE'],
                    "camera_ip": camera_config['IP'],
                    "image_data": snapshot_data,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "camera_name": camera_name,
                    "error": "Failed to capture snapshot"
                }
                
        except Exception as e:
            logger.error(
                "Error capturing from camera %s: %s", camera_name, str(e)
            )
            return {
                "success": False,
                "camera_name": camera_name,
                "error": str(e)
            }
