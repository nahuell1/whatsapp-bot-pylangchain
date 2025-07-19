"""
All Cameras function to capture snapshots from all configured cameras.
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime

from functions.camera import CameraFunction
from functions.base import bot_function

logger = logging.getLogger(__name__)


@bot_function("allcameras")
class AllCamerasFunction(CameraFunction):
    """Capture snapshots from all configured IP cameras simultaneously."""
    
    def __init__(self):
        """Initialize the All Cameras function."""
        # Initialize with camera discovery from parent
        super().__init__()
        
        # Override function metadata
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
        
        logger.info(f"AllCameras function initialized with {len(self.cameras)} cameras")
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the all cameras function.
        
        Args:
            **kwargs: Function parameters (none needed)
            
        Returns:
            Results from all camera captures
        """
        try:
            if not self.cameras:
                return self.format_error_response("No hay cámaras configuradas en el sistema")
            
            camera_names = list(self.cameras.keys())
            logger.info(f"Starting capture from {len(camera_names)} cameras: {camera_names}")
            
            # Capture from all cameras concurrently (with reasonable concurrency limit)
            semaphore = asyncio.Semaphore(3)  # Limit concurrent captures to avoid overload
            
            async def capture_with_semaphore(camera_name: str):
                async with semaphore:
                    return await self._capture_single_camera(camera_name)
            
            # Create tasks for all cameras
            tasks = [capture_with_semaphore(name) for name in camera_names]
            
            # Wait for all captures to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            successful_captures = []
            failed_captures = []
            
            for i, result in enumerate(results):
                camera_name = camera_names[i]
                
                if isinstance(result, Exception):
                    failed_captures.append({
                        "camera_name": camera_name,
                        "error": str(result)
                    })
                    logger.error(f"Camera {camera_name} failed: {str(result)}")
                elif result and result.get('success'):
                    successful_captures.append(result)
                    logger.info(f"Camera {camera_name} captured successfully")
                else:
                    failed_captures.append({
                        "camera_name": camera_name,
                        "error": "Unknown capture failure"
                    })
                    logger.warning(f"Camera {camera_name} failed with unknown error")
            
            # Format response
            total_cameras = len(camera_names)
            success_count = len(successful_captures)
            failed_count = len(failed_captures)
            
            if success_count == 0:
                return self.format_error_response(
                    f"No se pudo capturar imagen de ninguna de las {total_cameras} cámaras"
                )
            
            # Create response text
            response_text = f"📸 **Captura Múltiple de Cámaras**\n\n"
            response_text += f"✅ Exitosas: {success_count}\n"
            response_text += f"❌ Fallidas: {failed_count}\n"
            response_text += f"📱 Total: {total_cameras}\n\n"
            
            if successful_captures:
                response_text += "**Cámaras capturadas:**\n"
                for capture in successful_captures:
                    camera_name = capture['camera_name']
                    camera_type = capture['camera_type'].upper()
                    response_text += f"• {camera_name} ({camera_type})\n"
            
            if failed_captures:
                response_text += f"\n**Cámaras fallidas:**\n"
                for failure in failed_captures:
                    response_text += f"• {failure['camera_name']}\n"
            
            response_text += f"\n🕐 Completado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            
            return self.format_success_response(
                {
                    "total_cameras": total_cameras,
                    "successful_captures": successful_captures,
                    "failed_captures": failed_captures,
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "timestamp": datetime.now().isoformat()
                },
                response_text
            )
            
        except Exception as e:
            logger.error(f"Error in all cameras function: {str(e)}")
            return self.format_error_response(f"Error al capturar imágenes: {str(e)}")
    
    async def _capture_single_camera(self, camera_name: str) -> Dict[str, Any]:
        """
        Capture snapshot from a single camera.
        
        Args:
            camera_name: Name of the camera to capture from
            
        Returns:
            Capture result dictionary
        """
        try:
            camera_config = self.cameras[camera_name]
            
            logger.info(f"Capturing from camera: {camera_name}")
            snapshot_data = await self._capture_snapshot(camera_name, camera_config)
            
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
            logger.error(f"Error capturing from camera {camera_name}: {str(e)}")
            return {
                "success": False,
                "camera_name": camera_name,
                "error": str(e)
            }
