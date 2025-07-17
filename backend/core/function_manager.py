"""
Function manager for loading and executing bot functions.
"""

import os
import importlib.util
import logging
from typing import Dict, Any, List
import asyncio

from .config import settings

logger = logging.getLogger(__name__)


class FunctionManager:
    """Manages bot functions - loading, registration, and execution."""
    
    def __init__(self):
        """Initialize the function manager."""
        self.functions: Dict[str, Any] = {}
        self.functions_dir = os.path.join(os.path.dirname(__file__), "..", "functions")
    
    async def load_functions(self):
        """Load all functions from the functions directory."""
        logger.info(f"Loading functions from {self.functions_dir}")
        
        if not os.path.exists(self.functions_dir):
            logger.warning(f"Functions directory does not exist: {self.functions_dir}")
            return
        
        # Get all Python files in the functions directory
        function_files = [
            f for f in os.listdir(self.functions_dir)
            if f.endswith('.py') and not f.startswith('__') and f != 'base.py'
        ]
        
        logger.info(f"Found {len(function_files)} function files")
        
        for file_name in function_files:
            try:
                await self._load_function_from_file(file_name)
            except Exception as e:
                logger.error(f"Failed to load function from {file_name}: {str(e)}")
        
        logger.info(f"Successfully loaded {len(self.functions)} functions")
    
    async def _load_function_from_file(self, file_name: str):
        """Load a function from a Python file."""
        file_path = os.path.join(self.functions_dir, file_name)
        module_name = file_name[:-3]  # Remove .py extension
        
        # Load module dynamically
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find function classes in the module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                hasattr(attr, '__bases__') and 
                any(base.__name__ == 'FunctionBase' for base in attr.__bases__)):
                
                # Instantiate the function
                function_instance = attr()
                self.functions[function_instance.name] = function_instance
                logger.info(f"Loaded function: {function_instance.name}")
                break
    
    async def execute_function(self, function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a function with given parameters.
        
        Args:
            function_name: Name of the function to execute
            parameters: Parameters to pass to the function
            
        Returns:
            Function execution result
        """
        if function_name not in self.functions:
            error_msg = f"Function '{function_name}' not found"
            logger.error(error_msg)
            return {"error": error_msg, "response": f"Sorry, I don't know how to {function_name}"}
        
        function = self.functions[function_name]
        
        try:
            logger.info(f"Executing function: {function_name} with parameters: {parameters}")
            
            # Execute function with timeout
            result = await asyncio.wait_for(
                function.execute(**parameters),
                timeout=settings.FUNCTION_TIMEOUT
            )
            
            logger.info(f"Function {function_name} executed successfully")
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"Function '{function_name}' timed out after {settings.FUNCTION_TIMEOUT} seconds"
            logger.error(error_msg)
            return {"error": error_msg, "response": "The request timed out. Please try again."}
        
        except Exception as e:
            error_msg = f"Error executing function '{function_name}': {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "response": f"Sorry, I encountered an error while executing {function_name}"}
    
    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """Get definitions of all loaded functions."""
        return [
            {
                "name": func.name,
                "description": func.description,
                "parameters": func.parameters
            }
            for func in self.functions.values()
        ]
    
    async def reload_functions(self):
        """Reload all functions from the functions directory."""
        logger.info("Reloading functions...")
        self.functions.clear()
        await self.load_functions()
