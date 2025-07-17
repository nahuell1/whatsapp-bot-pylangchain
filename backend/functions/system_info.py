"""
System information function.
"""

import platform
import psutil
import os
import logging
from typing import Dict, Any
from datetime import datetime

from functions.base import FunctionBase

logger = logging.getLogger(__name__)


class SystemInfoFunction(FunctionBase):
    """Get system information."""
    
    def __init__(self):
        """Initialize the system info function."""
        super().__init__(
            name="system_info",
            description="Get system information including CPU, memory, disk usage, and more",
            parameters={
                "info_type": {
                    "type": "string",
                    "description": "Type of information to get (all, cpu, memory, disk, network, processes)",
                    "default": "all"
                },
                "detailed": {
                    "type": "boolean",
                    "description": "Whether to include detailed information",
                    "default": False
                }
            }
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
        return {
            "timestamp": datetime.now().isoformat(),
            "system": await self._get_system_info(),
            "cpu": await self._get_cpu_info(detailed),
            "memory": await self._get_memory_info(detailed),
            "disk": await self._get_disk_info(detailed),
            "network": await self._get_network_info(detailed) if detailed else {}
        }
    
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
