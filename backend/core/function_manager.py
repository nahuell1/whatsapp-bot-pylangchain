"""Function manager for loading and executing bot functions.

This module handles the dynamic discovery, loading, and execution
of bot function modules.
"""

import asyncio
import importlib.util
import logging
import os
from typing import Any, Dict, List

from functions.base import get_registered_functions

from .config import settings

logger = logging.getLogger(__name__)


class FunctionManager:
    """Manages bot functions - loading, registration, and execution.
    
    Attributes:
        functions: Dictionary of loaded function instances
        functions_dir: Directory path containing function modules
    """
    
    def __init__(self):
        """Initialize the function manager."""
        self.functions: Dict[str, Any] = {}
        self.functions_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "functions"
        )
    
    async def load_functions(self) -> None:
        """Load all functions from the functions directory.
        
        Discovers and loads all Python modules in the functions directory,
        triggering decorator-based registration and instantiation.
        """
        logger.info("Loading functions from %s", self.functions_dir)
        
        if not os.path.exists(self.functions_dir):
            logger.warning(
                "Functions directory does not exist: %s",
                self.functions_dir
            )
            return

        await self._import_all_modules()
        await self._instantiate_registered_functions()
        
        logger.info("Successfully loaded %d functions", len(self.functions))

    async def _import_all_modules(self) -> None:
        """Import all Python modules in the functions directory.
        
        Imports all .py files (except those starting with _) to trigger
        the @bot_function decorator registration.
        """
        for file_name in os.listdir(self.functions_dir):
            if file_name.endswith(".py") and not file_name.startswith("_"):
                try:
                    await self._import_module(file_name)
                except Exception as e:
                    logger.error(
                        "Failed to import module %s: %s",
                        file_name,
                        str(e)
                    )

    async def _import_module(self, file_name: str) -> None:
        """Import a single Python module dynamically.
        
        Args:
            file_name: Name of the Python file to import
        """
        file_path = os.path.join(self.functions_dir, file_name)
        module_name = f"functions.{file_name[:-3]}"
        
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        logger.debug("Imported module: %s", module_name)

    async def _instantiate_registered_functions(self) -> None:
        """Instantiate all registered functions.
        
        Creates instances of all functions that were registered via
        the @bot_function decorator.
        """
        registered_functions = get_registered_functions()
        
        for function_name, function_class in registered_functions.items():
            try:
                function_instance = function_class()
                self.functions[function_instance.name] = function_instance
                logger.info("Loaded function: %s", function_instance.name)
            except Exception as e:
                logger.error(
                    "Failed to instantiate function %s (%s): %s",
                    function_name,
                    function_class.__name__,
                    str(e)
                )

    async def _load_function_from_file(self, file_name: str):
        """
        Legacy method for loading functions - kept for backward compatibility.
        Use the new decorator-based system instead.
        """
        logger.warning("_load_function_from_file is deprecated. Use @bot_function decorator instead.")
        file_path = os.path.join(self.functions_dir, file_name)
        module_name = file_name[:-3]  # Remove .py extension
        
        # Load module dynamically
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find function classes in the module using the old method
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

    async def execute_function(
        self,
        function_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a function with given parameters.
        
        Args:
            function_name: Name of the function to execute
            parameters: Parameters to pass to the function
            
        Returns:
            Function execution result containing success status and response
        """
        if function_name not in self.functions:
            error_msg = f"Function '{function_name}' not found"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "response": f"Sorry, I don't know how to {function_name}"
            }
        
        function = self.functions[function_name]
        
        try:
            logger.info(
                "Executing function: %s with parameters: %s",
                function_name,
                parameters
            )
            
            result = await asyncio.wait_for(
                function.execute(**parameters),
                timeout=settings.FUNCTION_TIMEOUT
            )
            
            logger.info("Function %s executed successfully", function_name)
            return result
            
        except asyncio.TimeoutError:
            error_msg = (
                f"Function '{function_name}' timed out after "
                f"{settings.FUNCTION_TIMEOUT} seconds"
            )
            logger.error(error_msg)
            return {
                "error": error_msg,
                "response": "The request timed out. Please try again."
            }
        
        except Exception as e:
            error_msg = f"Error executing function '{function_name}': {str(e)}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "response": (
                    f"Sorry, I encountered an error while executing "
                    f"{function_name}"
                )
            }
    
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
    
    def get_function_metadata(self) -> List[Dict[str, Any]]:
        """Get command metadata for all loaded functions."""
        return [
            func.get_command_metadata()
            for func in self.functions.values()
        ]
    
    async def reload_functions(self):
        """Reload all functions from the functions directory."""
        logger.info("Reloading functions...")
        self.functions.clear()
        
        # Clear the function registry to avoid stale registrations
        from functions.base import clear_function_registry
        clear_function_registry()
        
        await self.load_functions()
