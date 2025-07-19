"""
Camera function to capture snapshots from various IP camera types.
"""

import os
import httpx
import logging
import asyncio
from typing import Dict, Any, List, Optional
import base64
import tempfile
from datetime import datetime
import subprocess
import xml.etree.ElementTree as ET

from functions.base import FunctionBase, bot_function

logger = logging.getLogger(__name__)


@bot_function("camera")
class CameraFunction(FunctionBase):
    """Capture snapshots from various IP camera types (RTSP, ONVIF, MJPEG, HTTP)."""
    
    def __init__(self):
        """Initialize the Camera function."""
        super().__init__(
            name="camera",
            description="Capture snapshot from a specific IP camera",
            parameters={
                "camera_name": {
                    "type": "string",
                    "description": "Name of the camera to capture from",
                    "required": False,
                    "default": "default"
                }
            },
            command_info={
                "usage": "!camera [nombre_camara]",
                "examples": [
                    "!camera",
                    "!camera kitchen",
                    "!camera front"
                ],
                "parameter_mapping": {
                    "camera_name": "first_arg"
                },
                "aliases": ["cam", "snapshot"]
            },
            intent_examples=[
                {
                    "message": "take a picture from kitchen camera",
                    "parameters": {"camera_name": "kitchen"}
                },
                {
                    "message": "show me the front camera",
                    "parameters": {"camera_name": "front"}
                }
            ]
        )
        
        # Load camera configurations from environment
        self.cameras = self._discover_cameras()
        logger.info(f"Discovered {len(self.cameras)} cameras: {list(self.cameras.keys())}")
    
    def _discover_cameras(self) -> Dict[str, Dict[str, str]]:
        """
        Auto-discover cameras from environment variables.
        Environment variables follow pattern: CAMERA_[NAME]_[CONFIG]
        Example: CAMERA_KITCHEN_IP=192.168.0.4
        """
        cameras = {}
        
        # Legacy support for single camera
        if os.getenv('CAMERA_IP'):
            cameras['default'] = {
                'IP': os.getenv('CAMERA_IP'),
                'PORT': os.getenv('CAMERA_PORT', '554'),
                'USERNAME': os.getenv('CAMERA_USERNAME', 'admin'),
                'PASSWORD': os.getenv('CAMERA_PASSWORD', ''),
                'TYPE': os.getenv('CAMERA_TYPE', 'rtsp').lower(),
                'PATH': os.getenv('CAMERA_PATH', '')
            }
        
        # Discover new pattern cameras: CAMERA_[NAME]_[CONFIG]
        for key, value in os.environ.items():
            if key.startswith('CAMERA_') and '_' in key[7:]:  # Skip 'CAMERA_' prefix
                parts = key[7:].split('_', 1)  # Split only on first underscore
                if len(parts) == 2:
                    camera_name, config_key = parts
                    camera_name = camera_name.lower()
                    
                    if camera_name not in cameras:
                        cameras[camera_name] = {
                            'IP': '',
                            'PORT': '554',
                            'USERNAME': 'admin',
                            'PASSWORD': '',
                            'TYPE': 'rtsp',
                            'PATH': ''
                        }
                    
                    # Map config keys to camera properties
                    config_key = config_key.upper()
                    if config_key in ['IP', 'PORT', 'USERNAME', 'PASSWORD', 'PATH']:
                        cameras[camera_name][config_key] = value
                    elif config_key == 'TYPE':
                        cameras[camera_name]['TYPE'] = value.lower()
        
        # Remove cameras without IP addresses
        cameras = {name: config for name, config in cameras.items() if config.get('IP')}
        
        return cameras
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the camera function.
        
        Args:
            **kwargs: Function parameters
            
        Returns:
            Camera snapshot result
        """
        try:
            params = self.validate_parameters(**kwargs)
            camera_name = params.get("camera_name", "default")
            
            # Check if camera exists
            if not self.cameras:
                return self.format_error_response("No hay cámaras configuradas en el sistema")
            
            # Use default camera if specified camera doesn't exist
            if camera_name not in self.cameras and "default" in self.cameras:
                camera_name = "default"
                logger.info(f"Camera not found, using default camera")
            elif camera_name not in self.cameras:
                available = ", ".join(self.cameras.keys())
                return self.format_error_response(
                    f"Cámara '{camera_name}' no encontrada. Disponibles: {available}"
                )
            
            logger.info(f"Capturing snapshot from camera '{camera_name}'")
            
            # Capture snapshot
            camera_config = self.cameras[camera_name]
            snapshot_data = await self._capture_snapshot(camera_name, camera_config)
            
            if snapshot_data:
                # Format response with image data
                response_text = f"📸 Imagen capturada de la cámara '{camera_name}'\n"
                response_text += f"🔧 Tipo: {camera_config['TYPE'].upper()}\n"
                response_text += f"📍 IP: {camera_config['IP']}\n"
                response_text += f"🕐 Capturada: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                
                return self.format_success_response(
                    {
                        "camera_name": camera_name,
                        "camera_type": camera_config['TYPE'],
                        "camera_ip": camera_config['IP'],
                        "image_data": snapshot_data,
                        "timestamp": datetime.now().isoformat()
                    },
                    response_text
                )
            else:
                return self.format_error_response(
                    f"No se pudo capturar imagen de la cámara '{camera_name}'"
                )
                
        except Exception as e:
            logger.error(f"Error in camera function: {str(e)}")
            return self.format_error_response(f"Error al capturar imagen: {str(e)}")
    
    async def _capture_snapshot(self, camera_name: str, config: Dict[str, str]) -> Optional[str]:
        """
        Capture snapshot from camera using appropriate method based on type.
        
        Args:
            camera_name: Name of the camera
            config: Camera configuration
            
        Returns:
            Base64 encoded image data or None if failed
        """
        camera_type = config.get('TYPE', 'rtsp').lower()
        
        logger.info(f"Attempting capture from {camera_type.upper()} camera: {camera_name}")
        
        try:
            if camera_type == 'onvif':
                return await self._capture_onvif_snapshot(config)
            elif camera_type == 'mjpeg':
                return await self._capture_mjpeg_snapshot(config)
            elif camera_type == 'http':
                return await self._capture_http_snapshot(config)
            elif camera_type == 'rtsp':
                return await self._capture_rtsp_snapshot(config)
            else:
                # Try RTSP as default fallback
                logger.warning(f"Unknown camera type '{camera_type}', trying RTSP")
                return await self._capture_rtsp_snapshot(config)
                
        except Exception as e:
            logger.error(f"Error capturing snapshot: {str(e)}")
            return None
    
    async def _capture_rtsp_snapshot(self, config: Dict[str, str]) -> Optional[str]:
        """Capture snapshot from RTSP stream using FFmpeg."""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Construct RTSP URL
            username = config.get('USERNAME', '')
            password = config.get('PASSWORD', '')
            ip = config['IP']
            port = config.get('PORT', '554')
            
            if username and password:
                rtsp_url = f"rtsp://{username}:{password}@{ip}:{port}/stream1"
            else:
                rtsp_url = f"rtsp://{ip}:{port}/stream1"
            
            # FFmpeg command
            cmd = [
                'ffmpeg', '-y', '-rtsp_transport', 'tcp',
                '-i', rtsp_url,
                '-frames:v', '1', '-q:v', '2',
                temp_path
            ]
            
            logger.debug(f"Running FFmpeg command: {' '.join(cmd[:6])} [RTSP_URL] {' '.join(cmd[7:])}")
            
            # Run FFmpeg with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15.0)
                
                if process.returncode == 0:
                    # Read and encode image
                    with open(temp_path, 'rb') as f:
                        image_data = f.read()
                    
                    if len(image_data) > 100:  # Minimum valid image size
                        encoded_data = base64.b64encode(image_data).decode('utf-8')
                        logger.info(f"RTSP snapshot captured successfully ({len(image_data)} bytes)")
                        return encoded_data
                        
                else:
                    logger.error(f"FFmpeg failed with return code: {process.returncode}")
                    logger.error(f"FFmpeg stderr: {stderr.decode()}")
                    
            except asyncio.TimeoutError:
                process.kill()
                logger.error("FFmpeg command timed out")
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error in RTSP capture: {str(e)}")
        
        return None
    
    async def _capture_onvif_snapshot(self, config: Dict[str, str]) -> Optional[str]:
        """Capture snapshot using ONVIF protocol or configured path."""
        try:
            # If we have a specific PATH configured, use it directly
            if config.get('PATH'):
                return await self._capture_http_with_path(config)
            
            # Otherwise try ONVIF discovery (simplified version)
            # For now, fallback to HTTP snapshot attempts
            logger.info("ONVIF discovery not implemented, trying HTTP fallback")
            return await self._capture_http_snapshot(config)
            
        except Exception as e:
            logger.error(f"Error in ONVIF capture: {str(e)}")
            return None
    
    async def _capture_http_with_path(self, config: Dict[str, str]) -> Optional[str]:
        """Capture snapshot using configured HTTP path."""
        try:
            ip = config['IP']
            port = config.get('PORT', '80')
            username = config.get('USERNAME', '')
            password = config.get('PASSWORD', '')
            path = config.get('PATH', '')
            
            # Determine protocol
            protocol = 'https' if port == '443' else 'http'
            
            # Ensure path starts with /
            if path and not path.startswith('/'):
                path = '/' + path
            
            # Construct URL
            if port in ['80', '443']:
                url = f"{protocol}://{ip}{path}"
            else:
                url = f"{protocol}://{ip}:{port}{path}"
            
            # Add authentication
            auth = None
            if username and password:
                auth = httpx.BasicAuth(username, password)
            
            logger.debug(f"Trying HTTP snapshot URL: {url}")
            
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                response = await client.get(url, auth=auth)
                response.raise_for_status()
                
                image_data = response.content
                if len(image_data) > 100 and self._is_valid_image(image_data):
                    encoded_data = base64.b64encode(image_data).decode('utf-8')
                    logger.info(f"HTTP snapshot captured successfully ({len(image_data)} bytes)")
                    return encoded_data
                    
        except Exception as e:
            logger.error(f"Error in HTTP path capture: {str(e)}")
        
        return None
    
    async def _capture_mjpeg_snapshot(self, config: Dict[str, str]) -> Optional[str]:
        """Capture snapshot from MJPEG stream."""
        try:
            ip = config['IP']
            port = config.get('PORT', '80')
            username = config.get('USERNAME', '')
            password = config.get('PASSWORD', '')
            path = config.get('PATH', '/video/mjpg/1')
            
            # Determine protocol
            protocol = 'https' if port == '443' else 'http'
            
            # Ensure path starts with /
            if path and not path.startswith('/'):
                path = '/' + path
            
            # Construct URL
            if port in ['80', '443']:
                url = f"{protocol}://{ip}{path}"
            else:
                url = f"{protocol}://{ip}:{port}{path}"
            
            # Add authentication
            auth = None
            if username and password:
                auth = httpx.BasicAuth(username, password)
            
            logger.debug(f"Trying MJPEG stream URL: {url}")
            
            async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                async with client.stream('GET', url, auth=auth) as response:
                    response.raise_for_status()
                    
                    # Read stream and extract first JPEG frame
                    content_type = response.headers.get('content-type', '')
                    
                    if 'multipart/x-mixed-replace' in content_type:
                        # Extract boundary
                        boundary = None
                        if 'boundary=' in content_type:
                            boundary = content_type.split('boundary=')[1].strip()
                        
                        image_buffer = bytearray()
                        collecting_image = False
                        
                        async for chunk in response.aiter_bytes():
                            if not collecting_image:
                                # Look for JPEG start marker
                                jpeg_start = chunk.find(b'\xff\xd8')
                                if jpeg_start != -1:
                                    image_buffer = bytearray(chunk[jpeg_start:])
                                    collecting_image = True
                            else:
                                # Look for JPEG end marker or boundary
                                image_buffer.extend(chunk)
                                
                                # Check for JPEG end
                                jpeg_end = bytes(image_buffer).find(b'\xff\xd9')
                                if jpeg_end != -1:
                                    # Found complete JPEG
                                    complete_image = bytes(image_buffer[:jpeg_end + 2])
                                    if self._is_valid_image(complete_image) and len(complete_image) > 1000:
                                        encoded_data = base64.b64encode(complete_image).decode('utf-8')
                                        logger.info(f"MJPEG frame captured successfully ({len(complete_image)} bytes)")
                                        return encoded_data
                                
                                # Prevent buffer from growing too large
                                if len(image_buffer) > 5 * 1024 * 1024:  # 5MB limit
                                    logger.warning("MJPEG frame too large, restarting capture")
                                    image_buffer = bytearray()
                                    collecting_image = False
                    else:
                        # Might be a direct image response
                        image_data = await response.aread()
                        if self._is_valid_image(image_data) and len(image_data) > 100:
                            encoded_data = base64.b64encode(image_data).decode('utf-8')
                            logger.info(f"Direct image captured from MJPEG URL ({len(image_data)} bytes)")
                            return encoded_data
                            
        except Exception as e:
            logger.error(f"Error in MJPEG capture: {str(e)}")
        
        return None
    
    async def _capture_http_snapshot(self, config: Dict[str, str]) -> Optional[str]:
        """Capture snapshot via direct HTTP request."""
        # Common HTTP snapshot URL patterns
        patterns = [
            '/snapshot.cgi',
            '/snapshot.jpg',
            '/image/jpeg.cgi',
            '/cgi-bin/snapshot.cgi',
            '/stw-cgi/image.cgi'
        ]
        
        for pattern in patterns:
            try:
                # Use the pattern as path
                temp_config = config.copy()
                temp_config['PATH'] = pattern
                result = await self._capture_http_with_path(temp_config)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"HTTP pattern {pattern} failed: {str(e)}")
                continue
        
        return None
    
    def _is_valid_image(self, data: bytes) -> bool:
        """Check if data appears to be a valid image."""
        if len(data) < 10:
            return False
        
        # Check for JPEG magic numbers
        if data[:2] == b'\xff\xd8':
            return True
            
        # Check for PNG magic numbers
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            return True
            
        return False
