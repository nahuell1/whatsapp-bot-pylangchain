"""System information function.

Provides detailed system metrics including CPU, memory, disk, network,
processes, and Raspberry Pi specific information.
"""

import logging
import os
import platform
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import psutil

from functions.base import FunctionBase, bot_function

logger = logging.getLogger(__name__)

TOP_PROCESSES_LIMIT = 10
TOP_PROCESSES_BRIEF = 5
TEMP_SCALE_THRESHOLD = 1000
MILLIDEGREES_TO_CELSIUS = 1000.0


@bot_function("system_info")
class SystemInfoFunction(FunctionBase):
    """Get system information including CPU, memory, disk, and RPi metrics.
    
    Provides comprehensive system monitoring with support for Raspberry Pi
    specific metrics like temperature and throttling status.
    """
    
    def __init__(self):
        """Initialize the system info function with supported info types."""
        super().__init__(
            name="system_info",
            description=(
                "Get system information including CPU, memory, disk usage, "
                "temperature (Raspberry Pi), and more"
            ),
            parameters={
                "info_type": {
                    "type": "string",
            "description": "Type of information to get (all, cpu, memory, disk, network, processes, rpi)",
                    "default": "all"
                },
                "detailed": {
                    "type": "boolean",
                    "description": "Whether to include detailed information",
                    "default": False
                }
            },
            command_info={
                "usage": "!system_info [tipo]",
                "examples": [
                    "!system_info",
                    "!system_info cpu",
                    "!system_info memory"
                ],
                "parameter_mapping": {
                    "info_type": "first_arg"  # Use first argument as info_type
                }
            },
            intent_examples=[
                {
                    "message": "show system information",
                    "parameters": {}
                },
                {
                    "message": "check CPU usage",
                    "parameters": {"info_type": "cpu"}
                }
            ]
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the system info function.
        
        Args:
            **kwargs: Function parameters
            
        Returns:
            System information
        """
        try:
            # Validate parameters
            params = self.validate_parameters(**kwargs)
            info_type = params.get("info_type", "all")
            detailed = params.get("detailed", False)
            
            logger.info(f"Getting system info: {info_type}")
            
            # Get system information
            if info_type == "all":
                system_info = await self._get_all_info(detailed)
            elif info_type == "cpu":
                system_info = await self._get_cpu_info(detailed)
            elif info_type == "memory":
                system_info = await self._get_memory_info(detailed)
            elif info_type == "disk":
                system_info = await self._get_disk_info(detailed)
            elif info_type == "network":
                system_info = await self._get_network_info(detailed)
            elif info_type == "processes":
                system_info = await self._get_process_info(detailed)
            elif info_type == "rpi":
                system_info = await self._get_rpi_extras()
            else:
                return self.format_error_response(f"Unknown info type: {info_type}")
            
            # Format response
            response_message = self._format_system_info_response(system_info, info_type)
            
            return self.format_success_response(system_info, response_message)
            
        except Exception as e:
            logger.error(f"Error in system info function: {str(e)}")
            return self.format_error_response(str(e))
    
    async def _get_all_info(self, detailed: bool) -> Dict[str, Any]:
        """Get all system information."""
        all_info = {
            "timestamp": datetime.now().isoformat(),
            "system": await self._get_system_info(),
            "cpu": await self._get_cpu_info(detailed),
            "memory": await self._get_memory_info(detailed),
            "disk": await self._get_disk_info(detailed),
            "network": await self._get_network_info(detailed) if detailed else {}
        }
        # Raspberry Pi extras (best-effort) & container limits
        try:
            all_info["rpi"] = await self._get_rpi_extras()
        except Exception:  # pragma: no cover - non-critical
            all_info["rpi"] = {}
        try:
            all_info["container"] = self._get_container_limits()
        except Exception:
            all_info["container"] = {}
        return all_info
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information."""
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "processor": platform.processor(),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "python_version": platform.python_version()
        }
    
    async def _get_cpu_info(self, detailed: bool) -> Dict[str, Any]:
        """Get CPU information."""
        cpu_info = {
            "physical_cores": psutil.cpu_count(logical=False),
            "total_cores": psutil.cpu_count(logical=True),
            "max_frequency": psutil.cpu_freq().max if psutil.cpu_freq() else None,
            "current_frequency": psutil.cpu_freq().current if psutil.cpu_freq() else None,
            "cpu_usage": psutil.cpu_percent(interval=1),
            "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None
        }
        
        if detailed:
            cpu_info["per_core_usage"] = psutil.cpu_percent(interval=1, percpu=True)

        # Attempt to append temperature
        temp_c = self._read_cpu_temperature()
        if temp_c is not None:
            cpu_info["temperature_c"] = temp_c
        
        return cpu_info
    
    async def _get_memory_info(self, detailed: bool) -> Dict[str, Any]:
        """Get memory information."""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        memory_info = {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percentage": memory.percent,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percentage": swap.percent
        }
        
        if detailed:
            memory_info.update({
                "buffers": memory.buffers if hasattr(memory, 'buffers') else None,
                "cached": memory.cached if hasattr(memory, 'cached') else None,
                "shared": memory.shared if hasattr(memory, 'shared') else None
            })
        
        return memory_info
    
    async def _get_disk_info(self, detailed: bool) -> Dict[str, Any]:
        """Get disk information."""
        disk_info = {}
        
        # Get disk usage for root partition
        disk_usage = psutil.disk_usage('/')
        disk_info["root"] = {
            "total": disk_usage.total,
            "used": disk_usage.used,
            "free": disk_usage.free,
            "percentage": (disk_usage.used / disk_usage.total) * 100
        }
        
        if detailed:
            # Get all disk partitions
            partitions = psutil.disk_partitions()
            disk_info["partitions"] = []
            
            for partition in partitions:
                try:
                    partition_usage = psutil.disk_usage(partition.mountpoint)
                    disk_info["partitions"].append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "filesystem": partition.fstype,
                        "total": partition_usage.total,
                        "used": partition_usage.used,
                        "free": partition_usage.free,
                        "percentage": (partition_usage.used / partition_usage.total) * 100
                    })
                except PermissionError:
                    # Skip partitions that can't be accessed
                    continue
        
        return disk_info
    
    async def _get_network_info(self, detailed: bool) -> Dict[str, Any]:
        """Get network information."""
        net_io = psutil.net_io_counters()
        
        network_info = {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        }
        
        if detailed:
            # Get network interfaces
            interfaces = psutil.net_if_addrs()
            network_info["interfaces"] = {}
            
            for interface_name, interface_addresses in interfaces.items():
                network_info["interfaces"][interface_name] = []
                for address in interface_addresses:
                    network_info["interfaces"][interface_name].append({
                        "family": str(address.family),
                        "address": address.address,
                        "netmask": address.netmask,
                        "broadcast": address.broadcast
                    })
        
        return network_info
    
    async def _get_process_info(self, detailed: bool) -> Dict[str, Any]:
        """Get process information."""
        processes = []
        
        # Get top processes by CPU usage
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        
        process_info = {
            "total_processes": len(processes),
            "top_processes": processes[:10] if detailed else processes[:5]
        }
        
        return process_info

    async def _get_rpi_extras(self) -> Dict[str, Any]:
        """Get Raspberry Pi specific metrics (best-effort inside Docker)."""
        rpi_info: Dict[str, Any] = {}
        # Detect model
        model_path = Path('/proc/device-tree/model')
        if model_path.exists():
            try:
                rpi_info['model'] = model_path.read_text(errors='ignore').strip('\x00')
            except Exception:
                pass

        # Temperature (reuse helper for consistency)
        temp_c = self._read_cpu_temperature()
        if temp_c is not None:
            rpi_info['cpu_temperature_c'] = temp_c

        # Throttling flags via vcgencmd (if available)
        vcgencmd = shutil.which('vcgencmd') if 'shutil' in globals() else None
        if vcgencmd is None:
            import shutil as _shutil
            vcgencmd = _shutil.which('vcgencmd')
        if vcgencmd:
            try:
                raw = subprocess.check_output([vcgencmd, 'get_throttled'], text=True).strip()
                rpi_info['throttled_raw'] = raw
                # raw format: throttled=0x50005
                if '=' in raw:
                    hex_part = raw.split('=')[1]
                    value = int(hex_part, 16)
                    rpi_info['throttled_flags'] = self._decode_throttle_flags(value)
            except Exception:  # pragma: no cover
                pass

        return rpi_info

    def _decode_throttle_flags(self, value: int) -> Dict[str, bool]:
        """Decode Raspberry Pi throttled flags per official docs."""
        flags = {
            'under_voltage_now': bool(value & (1 << 0)),
            'freq_capped_now': bool(value & (1 << 1)),
            'throttled_now': bool(value & (1 << 2)),
            'under_voltage_past': bool(value & (1 << 16)),
            'freq_capped_past': bool(value & (1 << 17)),
            'throttled_past': bool(value & (1 << 18)),
        }
        return flags

    def _read_cpu_temperature(self):
        """Read CPU temperature in Celsius from common Raspberry Pi thermal zones."""
        # Common path
        candidates = [
            '/sys/class/thermal/thermal_zone0/temp',
            '/sys/class/hwmon/hwmon0/temp1_input'
        ]
        for path in candidates:
            try:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        raw = f.read().strip()
                        if raw.isdigit():
                            milli = int(raw)
                            if milli > 1000:
                                return milli / 1000.0
                            return float(milli)
                        # Sometimes "42000" etc.
                        try:
                            val = float(raw)
                            if val > 1000:
                                val = val / 1000.0
                            return val
                        except ValueError:
                            continue
            except Exception:  # pragma: no cover
                continue
        # Fallback to vcgencmd if available
        try:
            import shutil as _shutil
            vcgencmd = _shutil.which('vcgencmd')
            if vcgencmd:
                out = subprocess.check_output([vcgencmd, 'measure_temp'], text=True).strip()
                # format temp=42.0'C
                if '=' in out:
                    part = out.split('=')[1]
                    if part.endswith("'C"):
                        return float(part[:-2])
        except Exception:  # pragma: no cover
            pass
        return None

    def _get_container_limits(self) -> Dict[str, Any]:
        """Get container (cgroup) resource limits if available."""
        limits: Dict[str, Any] = {}
        # Memory limits (cgroup v1 & v2)
        mem_candidates = [
            '/sys/fs/cgroup/memory.max',  # v2
            '/sys/fs/cgroup/memory/memory.limit_in_bytes'  # v1
        ]
        for path in mem_candidates:
            if os.path.exists(path):
                try:
                    raw = Path(path).read_text().strip()
                    if raw not in ('max', ''):
                        limits['memory_limit_bytes'] = int(raw)
                        break
                except Exception:
                    continue
        # CPU quota
        cpu_quota_paths = [
            ('/sys/fs/cgroup/cpu.max', 'v2'),
            ('/sys/fs/cgroup/cpu/cpu.cfs_quota_us', 'v1_quota'),
            ('/sys/fs/cgroup/cpu/cpu.cfs_period_us', 'v1_period')
        ]
        cpu_data = {}
        for path, key in cpu_quota_paths:
            if os.path.exists(path):
                try:
                    cpu_data[key] = Path(path).read_text().strip()
                except Exception:
                    pass
        # Interpret v2 cpu.max format: "max 100000" or "200000 100000" (quota period)
        if 'v2' in cpu_data:
            parts = cpu_data['v2'].split()
            if len(parts) == 2 and parts[0] != 'max':
                try:
                    quota = int(parts[0]); period = int(parts[1])
                    limits['cpu_quota'] = quota
                    limits['cpu_period'] = period
                    limits['cpu_limit_cores_est'] = round(quota / period, 2) if period > 0 else None
                except Exception:
                    pass
        else:
            if 'v1_quota' in cpu_data and 'v1_period' in cpu_data:
                try:
                    quota = int(cpu_data['v1_quota']); period = int(cpu_data['v1_period'])
                    if quota > 0 and period > 0:
                        limits['cpu_limit_cores_est'] = round(quota / period, 2)
                except Exception:
                    pass
        return limits
    
    def _format_system_info_response(self, system_info: Dict[str, Any], info_type: str) -> str:
        """Format system information response."""
        try:
            response = f"🖥️ System Information ({info_type})\n\n"
            
            if info_type == "all":
                # System info
                system = system_info.get("system", {})
                response += f"💻 Platform: {system.get('platform')} {system.get('platform_release')}\n"
                response += f"🏠 Hostname: {system.get('hostname')}\n"
                response += f"⚙️ Architecture: {system.get('architecture')}\n\n"
                
                # CPU info
                cpu = system_info.get("cpu", {})
                response += f"🔥 CPU Usage: {cpu.get('cpu_usage', 0):.1f}%\n"
                response += f"🧠 Cores: {cpu.get('physical_cores')} physical, {cpu.get('total_cores')} total\n"
                if cpu.get('current_frequency'):
                    response += f"⚡ Frequency: {cpu.get('current_frequency'):.0f} MHz\n"
                if cpu.get('temperature_c') is not None:
                    response += f"🌡️ CPU Temp: {cpu.get('temperature_c'):.1f}°C\n"
                response += "\n"
                
                # Memory info
                memory = system_info.get("memory", {})
                total_gb = memory.get("total", 0) / (1024**3)
                used_gb = memory.get("used", 0) / (1024**3)
                response += f"🧮 Memory: {used_gb:.1f}GB / {total_gb:.1f}GB ({memory.get('percentage', 0):.1f}%)\n"
                
                # Disk info
                disk = system_info.get("disk", {})
                root_disk = disk.get("root", {})
                if root_disk:
                    total_gb = root_disk.get("total", 0) / (1024**3)
                    used_gb = root_disk.get("used", 0) / (1024**3)
                    response += f"💾 Disk: {used_gb:.1f}GB / {total_gb:.1f}GB ({root_disk.get('percentage', 0):.1f}%)\n"
                
            elif info_type == "cpu":
                response += f"🔥 CPU Usage: {system_info.get('cpu_usage', 0):.1f}%\n"
                response += f"🧠 Cores: {system_info.get('physical_cores')} physical, {system_info.get('total_cores')} total\n"
                if system_info.get('current_frequency'):
                    response += f"⚡ Frequency: {system_info.get('current_frequency'):.0f} MHz\n"
                if system_info.get('temperature_c') is not None:
                    response += f"🌡️ CPU Temp: {system_info.get('temperature_c'):.1f}°C\n"
            elif info_type == "rpi":
                if system_info.get('model'):
                    response += f"🍓 Model: {system_info.get('model')}\n"
                if system_info.get('cpu_temperature_c') is not None:
                    response += f"🌡️ CPU Temp: {system_info.get('cpu_temperature_c'):.1f}°C\n"
                flags = system_info.get('throttled_flags') or {}
                if flags:
                    active = [k for k, v in flags.items() if v and k.endswith('_now')]
                    past = [k for k, v in flags.items() if v and k.endswith('_past')]
                    if active:
                        response += f"⚠️ Throttle Now: {', '.join(active)}\n"
                    if past:
                        response += f"🕓 Throttle Past: {', '.join(past)}\n"
                
            elif info_type == "memory":
                total_gb = system_info.get("total", 0) / (1024**3)
                used_gb = system_info.get("used", 0) / (1024**3)
                response += f"🧮 Memory: {used_gb:.1f}GB / {total_gb:.1f}GB ({system_info.get('percentage', 0):.1f}%)\n"
                
                swap_total_gb = system_info.get("swap_total", 0) / (1024**3)
                swap_used_gb = system_info.get("swap_used", 0) / (1024**3)
                response += f"🔄 Swap: {swap_used_gb:.1f}GB / {swap_total_gb:.1f}GB ({system_info.get('swap_percentage', 0):.1f}%)\n"
                
            elif info_type == "disk":
                root_disk = system_info.get("root", {})
                if root_disk:
                    total_gb = root_disk.get("total", 0) / (1024**3)
                    used_gb = root_disk.get("used", 0) / (1024**3)
                    free_gb = root_disk.get("free", 0) / (1024**3)
                    response += f"💾 Root Disk: {used_gb:.1f}GB / {total_gb:.1f}GB ({root_disk.get('percentage', 0):.1f}%)\n"
                    response += f"🆓 Free Space: {free_gb:.1f}GB\n"
                
            elif info_type == "processes":
                response += f"📊 Total Processes: {system_info.get('total_processes', 0)}\n\n"
                response += "Top Processes:\n"
                for proc in system_info.get('top_processes', [])[:5]:
                    response += f"• {proc.get('name', 'Unknown')}: {proc.get('cpu_percent', 0):.1f}% CPU\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting system info response: {str(e)}")
            return f"System information retrieved successfully!"
