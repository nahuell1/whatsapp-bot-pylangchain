"""Camera function to capture snapshots from various IP camera types.

Supports RTSP, ONVIF, MJPEG, and HTTP cameras with automatic discovery
from environment variables.
"""

import asyncio
import base64
import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from functions.base import FunctionBase, bot_function

logger = logging.getLogger(__name__)

DEFAULT_PORT = "554"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = ""
DEFAULT_CAMERA_TYPE = "rtsp"
DEFAULT_CAMERA_PATH = ""
FFMPEG_TIMEOUT_SECONDS = 15.0
HTTP_TIMEOUT_SECONDS = 10.0
MJPEG_TIMEOUT_SECONDS = 15.0
MIN_IMAGE_SIZE_BYTES = 100
VALID_IMAGE_SIZE_BYTES = 1000
MAX_MJPEG_BUFFER_BYTES = 5 * 1024 * 1024
CAMERA_ENV_PREFIX = "CAMERA_"


@bot_function("camera")
class CameraFunction(FunctionBase):
    """Capture snapshots from IP cameras (RTSP, ONVIF, MJPEG, HTTP).
    
    Automatically discovers cameras from environment variables following
    the pattern CAMERA_[NAME]_[CONFIG] (e.g., CAMERA_KITCHEN_IP).
    """
    
    def __init__(self):
        """Initialize the camera function with discovered cameras."""
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
        
        self.cameras = self._discover_cameras()
        logger.info(
            "Discovered %d cameras: %s",
            len(self.cameras),
            list(self.cameras.keys())
        )
    
    def _discover_cameras(self) -> Dict[str, Dict[str, str]]:
        """Auto-discover cameras from environment variables.
        
        Supports two patterns:
        1. Legacy: CAMERA_IP, CAMERA_PORT, etc. (single camera as 'default')
        2. Named: CAMERA_[NAME]_[CONFIG] (e.g., CAMERA_KITCHEN_IP)
        
        Returns:
            Dict mapping camera names to their configuration dicts
        """
        cameras = {}
        
        if os.getenv('CAMERA_IP'):
            cameras['default'] = {
                'IP': os.getenv('CAMERA_IP'),
                'PORT': os.getenv('CAMERA_PORT', DEFAULT_PORT),
                'USERNAME': os.getenv('CAMERA_USERNAME', DEFAULT_USERNAME),
                'PASSWORD': os.getenv('CAMERA_PASSWORD', DEFAULT_PASSWORD),
                'TYPE': os.getenv('CAMERA_TYPE', DEFAULT_CAMERA_TYPE).lower(),
                'PATH': os.getenv('CAMERA_PATH', DEFAULT_CAMERA_PATH)
            }
        
        for key, value in os.environ.items():
            if key.startswith(CAMERA_ENV_PREFIX) and '_' in key[7:]:
                parts = key[7:].split('_', 1)
                if len(parts) == 2:
                    camera_name, config_key = parts
                    camera_name = camera_name.lower()
                    
                    if camera_name not in cameras:
                        cameras[camera_name] = {
                            'IP': '',
                            'PORT': DEFAULT_PORT,
                            'USERNAME': DEFAULT_USERNAME,
                            'PASSWORD': DEFAULT_PASSWORD,
                            'TYPE': DEFAULT_CAMERA_TYPE,
                            'PATH': DEFAULT_CAMERA_PATH
                        }
                    
                    config_key = config_key.upper()
                    if config_key in ['IP', 'PORT', 'USERNAME', 'PASSWORD', 'PATH']:
                        cameras[camera_name][config_key] = value
                    elif config_key == 'TYPE':
                        cameras[camera_name]['TYPE'] = value.lower()
        
        cameras = {
            name: config for name, config in cameras.items()
            if config.get('IP')
        }
        
        return cameras
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the camera function.
        
        Args:
            **kwargs: Function parameters (camera_name)
            
        Returns:
            Dict with snapshot data and formatted message
        """
        try:
            params = self.validate_parameters(**kwargs)
            camera_name = params.get("camera_name", "default")
            
            if not self.cameras:
                return self.format_error_response(
                    "No cameras configured in the system"
                )
            
            if camera_name not in self.cameras and "default" in self.cameras:
                camera_name = "default"
                logger.info("Camera not found, using default camera")
            elif camera_name not in self.cameras:
                available = ", ".join(self.cameras.keys())
                return self.format_error_response(
                    f"Camera '{camera_name}' not found. "
                    f"Available: {available}"
                )
            
            logger.info("Capturing snapshot from camera '%s'", camera_name)
            
            camera_config = self.cameras[camera_name]
            snapshot_data = await self._capture_snapshot(
                camera_name, camera_config
            )
            
            if snapshot_data:
                timestamp = datetime.now()
                response_text = (
                    f"📸 Image captured from camera '{camera_name}'\n"
                    f"🔧 Type: {camera_config['TYPE'].upper()}\n"
                    f"📍 IP: {camera_config['IP']}\n"
                    f"🕐 Captured: {timestamp.strftime('%d/%m/%Y %H:%M:%S')}"
                )
                
                return self.format_success_response(
                    {
                        "camera_name": camera_name,
                        "camera_type": camera_config['TYPE'],
                        "camera_ip": camera_config['IP'],
                        "image_data": snapshot_data,
                        "timestamp": timestamp.isoformat()
                    },
                    response_text
                )
            else:
                return self.format_error_response(
                    f"Could not capture image from camera '{camera_name}'"
                )
                
        except Exception as e:
            logger.error("Error in camera function: %s", str(e))
            return self.format_error_response(
                f"Error capturing image: {str(e)}"
            )
    
    async def _capture_snapshot(
        self,
        camera_name: str,
        config: Dict[str, str]
    ) -> Optional[str]:
        """Capture snapshot using appropriate method based on camera type.
        
        Args:
            camera_name: Name of the camera
            config: Camera configuration dict
            
        Returns:
            Base64 encoded image data or None if capture failed
        """
        camera_type = config.get('TYPE', DEFAULT_CAMERA_TYPE).lower()
        
        logger.info(
            "Attempting capture from %s camera: %s",
            camera_type.upper(),
            camera_name
        )
        
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
                logger.warning(
                    "Unknown camera type '%s', trying RTSP",
                    camera_type
                )
                return await self._capture_rtsp_snapshot(config)
                
        except Exception as e:
            logger.error("Error capturing snapshot: %s", str(e))
            return None
    
    async def _capture_rtsp_snapshot(
        self,
        config: Dict[str, str]
    ) -> Optional[str]:
        """Capture snapshot from RTSP stream using FFmpeg.
        
        Args:
            config: Camera configuration with IP, port, credentials
            
        Returns:
            Base64 encoded JPEG image or None on failure
        """
        try:
            with tempfile.NamedTemporaryFile(
                suffix='.jpg', delete=False
            ) as temp_file:
                temp_path = temp_file.name
            
            username = config.get('USERNAME', '')
            password = config.get('PASSWORD', '')
            ip = config['IP']
            port = config.get('PORT', DEFAULT_PORT)
            
            if username and password:
                rtsp_url = f"rtsp://{username}:{password}@{ip}:{port}/stream1"
            else:
                rtsp_url = f"rtsp://{ip}:{port}/stream1"
            
            cmd = [
                'ffmpeg', '-y', '-rtsp_transport', 'tcp',
                '-i', rtsp_url,
                '-frames:v', '1', '-q:v', '2',
                temp_path
            ]
            
            logger.debug(
                "Running FFmpeg command: %s [RTSP_URL] %s",
                ' '.join(cmd[:6]),
                ' '.join(cmd[7:])
            )
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=FFMPEG_TIMEOUT_SECONDS
                )
                
                if process.returncode == 0:
                    with open(temp_path, 'rb') as f:
                        image_data = f.read()
                    
                    if len(image_data) > MIN_IMAGE_SIZE_BYTES:
                        encoded_data = base64.b64encode(image_data).decode()
                        logger.info(
                            "RTSP snapshot captured successfully (%d bytes)",
                            len(image_data)
                        )
                        return encoded_data
                        
                else:
                    logger.error(
                        "FFmpeg failed with return code: %d",
                        process.returncode
                    )
                    logger.error("FFmpeg stderr: %s", stderr.decode())
                    
            except asyncio.TimeoutError:
                process.kill()
                logger.error("FFmpeg command timed out")
                
            finally:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                    
        except Exception as e:
            logger.error("Error in RTSP capture: %s", str(e))
        
        return None
    
    async def _capture_onvif_snapshot(
        self,
        config: Dict[str, str]
    ) -> Optional[str]:
        """Capture snapshot using ONVIF protocol or configured path.
        
        Args:
            config: Camera configuration
            
        Returns:
            Base64 encoded image or None
        """
        try:
            if config.get('PATH'):
                return await self._capture_http_with_path(config)
            
            logger.info("ONVIF discovery not implemented, trying HTTP fallback")
            return await self._capture_http_snapshot(config)
            
        except Exception as e:
            logger.error("Error in ONVIF capture: %s", str(e))
            return None
    
    async def _capture_http_with_path(
        self,
        config: Dict[str, str]
    ) -> Optional[str]:
        """Capture snapshot using configured HTTP path.
        
        Args:
            config: Camera configuration with PATH specified
            
        Returns:
            Base64 encoded image or None
        """
        try:
            ip = config['IP']
            port = config.get('PORT', '80')
            username = config.get('USERNAME', '')
            password = config.get('PASSWORD', '')
            path = config.get('PATH', '')
            
            protocol = 'https' if port == '443' else 'http'
            
            if path and not path.startswith('/'):
                path = '/' + path
            
            if port in ['80', '443']:
                url = f"{protocol}://{ip}{path}"
            else:
                url = f"{protocol}://{ip}:{port}{path}"
            
            auth = None
            if username and password:
                auth = httpx.BasicAuth(username, password)
            
            logger.debug("Trying HTTP snapshot URL: %s", url)
            
            async with httpx.AsyncClient(
                verify=False,
                timeout=HTTP_TIMEOUT_SECONDS
            ) as client:
                response = await client.get(url, auth=auth)
                response.raise_for_status()
                
                image_data = response.content
                if (len(image_data) > MIN_IMAGE_SIZE_BYTES
                        and self._is_valid_image(image_data)):
                    encoded_data = base64.b64encode(image_data).decode()
                    logger.info(
                        "HTTP snapshot captured successfully (%d bytes)",
                        len(image_data)
                    )
                    return encoded_data
                    
        except Exception as e:
            logger.error("Error in HTTP path capture: %s", str(e))
        
        return None
    
    async def _capture_mjpeg_snapshot(
        self,
        config: Dict[str, str]
    ) -> Optional[str]:
        """Capture snapshot from MJPEG stream.
        
        Extracts the first complete JPEG frame from an MJPEG stream.
        
        Args:
            config: Camera configuration
            
        Returns:
            Base64 encoded JPEG or None
        """
        try:
            ip = config['IP']
            port = config.get('PORT', '80')
            username = config.get('USERNAME', '')
            password = config.get('PASSWORD', '')
            path = config.get('PATH', '/video/mjpg/1')
            
            protocol = 'https' if port == '443' else 'http'
            
            if path and not path.startswith('/'):
                path = '/' + path
            
            if port in ['80', '443']:
                url = f"{protocol}://{ip}{path}"
            else:
                url = f"{protocol}://{ip}:{port}{path}"
            
            auth = None
            if username and password:
                auth = httpx.BasicAuth(username, password)
            
            logger.debug("Trying MJPEG stream URL: %s", url)
            
            async with httpx.AsyncClient(
                verify=False,
                timeout=MJPEG_TIMEOUT_SECONDS
            ) as client:
                async with client.stream('GET', url, auth=auth) as response:
                    response.raise_for_status()
                    
                    content_type = response.headers.get('content-type', '')
                    
                    if 'multipart/x-mixed-replace' in content_type:
                        image_buffer = bytearray()
                        collecting_image = False
                        
                        async for chunk in response.aiter_bytes():
                            if not collecting_image:
                                jpeg_start = chunk.find(b'\xff\xd8')
                                if jpeg_start != -1:
                                    image_buffer = bytearray(chunk[jpeg_start:])
                                    collecting_image = True
                            else:
                                image_buffer.extend(chunk)
                                
                                jpeg_end = bytes(image_buffer).find(b'\xff\xd9')
                                if jpeg_end != -1:
                                    complete_image = bytes(
                                        image_buffer[:jpeg_end + 2]
                                    )
                                    if (self._is_valid_image(complete_image)
                                            and len(complete_image)
                                            > VALID_IMAGE_SIZE_BYTES):
                                        encoded_data = base64.b64encode(
                                            complete_image
                                        ).decode()
                                        logger.info(
                                            "MJPEG frame captured successfully "
                                            "(%d bytes)",
                                            len(complete_image)
                                        )
                                        return encoded_data
                                
                                if len(image_buffer) > MAX_MJPEG_BUFFER_BYTES:
                                    logger.warning(
                                        "MJPEG frame too large, restarting"
                                    )
                                    image_buffer = bytearray()
                                    collecting_image = False
                    else:
                        image_data = await response.aread()
                        if (self._is_valid_image(image_data)
                                and len(image_data) > MIN_IMAGE_SIZE_BYTES):
                            encoded_data = base64.b64encode(
                                image_data
                            ).decode()
                            logger.info(
                                "Direct image captured from MJPEG URL "
                                "(%d bytes)",
                                len(image_data)
                            )
                            return encoded_data
                            
        except Exception as e:
            logger.error("Error in MJPEG capture: %s", str(e))
        
        return None
    
    async def _capture_http_snapshot(
        self,
        config: Dict[str, str]
    ) -> Optional[str]:
        """Capture snapshot via direct HTTP request.
        
        Tries common camera snapshot URL patterns.
        
        Args:
            config: Camera configuration
            
        Returns:
            Base64 encoded image or None
        """
        patterns = [
            '/snapshot.cgi',
            '/snapshot.jpg',
            '/image/jpeg.cgi',
            '/cgi-bin/snapshot.cgi',
            '/stw-cgi/image.cgi'
        ]
        
        for pattern in patterns:
            try:
                temp_config = config.copy()
                temp_config['PATH'] = pattern
                result = await self._capture_http_with_path(temp_config)
                if result:
                    return result
            except Exception as e:
                logger.debug("HTTP pattern %s failed: %s", pattern, str(e))
                continue
        
        return None
    
    @staticmethod
    def _is_valid_image(data: bytes) -> bool:
        """Check if data appears to be a valid image.
        
        Args:
            data: Binary image data
            
        Returns:
            True if data starts with JPEG or PNG magic numbers
        """
        if len(data) < 10:
            return False
        
        return (
            data[:2] == b'\xff\xd8'
            or data[:8] == b'\x89PNG\r\n\x1a\n'
        )
