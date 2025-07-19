"""
Base class for all bot functions.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Set, Type, Optional
import logging

logger = logging.getLogger(__name__)

# Global registry for bot functions
_REGISTERED_FUNCTIONS: Dict[str, Type['FunctionBase']] = {}


def bot_function(name: Optional[str] = None):
    """
    Decorator to register a class as a bot function.
    
    This decorator allows for more flexible inheritance while still
    maintaining automatic discovery of bot functions.
    
    Args:
        name: Optional name for the function. If not provided,
              uses the class name in lowercase.
    
    Example:
        @bot_function("weather")
        class WeatherFunction(FunctionBase):
            pass
        
        @bot_function()
        class CustomBase(FunctionBase):
            pass
            
        @bot_function("camera")  
        class CameraFunction(CustomBase):
            pass
    """
    def decorator(cls: Type['FunctionBase']) -> Type['FunctionBase']:
        # Ensure the class is a subclass of FunctionBase somewhere in its hierarchy
        if not issubclass(cls, FunctionBase):
            raise TypeError(f"Class {cls.__name__} must inherit from FunctionBase")
        
        # Determine function name
        function_name = name or cls.__name__.lower().replace('function', '')
        
        # Register the function
        _REGISTERED_FUNCTIONS[function_name] = cls
        logger.debug(f"Registered bot function: {function_name} -> {cls.__name__}")
        
        return cls
    return decorator


def get_registered_functions() -> Dict[str, Type['FunctionBase']]:
    """Get all registered bot functions."""
    return _REGISTERED_FUNCTIONS.copy()


def clear_function_registry():
    """Clear the function registry (useful for testing)."""
    global _REGISTERED_FUNCTIONS
    _REGISTERED_FUNCTIONS.clear()


class FunctionBase(ABC):
    """Base class for all bot functions."""
    
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], command_info: Dict[str, Any] = None, intent_examples: list = None):
        """
        Initialize a function.
        
        Args:
            name: Function name
            description: Function description
            parameters: Function parameters schema
            command_info: Command-specific information for direct execution
            intent_examples: Examples for intent detection training
        """
        self.name = name
        self.description = description
        self.parameters = parameters
        self.command_info = command_info or {}
        self.intent_examples = intent_examples or []
        logger.info(f"Initialized function: {name}")
    
    def get_command_metadata(self) -> Dict[str, Any]:
        """
        Get command metadata for direct execution.
        
        Returns:
            Command metadata including usage examples and parameter mapping
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "command_info": self.command_info,
            "intent_examples": self.intent_examples
        }
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the function with given parameters.
        
        Args:
            **kwargs: Function parameters
            
        Returns:
            Dict containing function result and response message
        """
        pass
    
    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """
        Validate function parameters.
        
        Args:
            **kwargs: Parameters to validate
            
        Returns:
            Validated parameters
            
        Raises:
            ValueError: If parameters are invalid
        """
        validated = {}
        
        for param_name, param_schema in self.parameters.items():
            value = kwargs.get(param_name)
            
            # Check if required parameter is missing
            if param_schema.get("required", False) and value is None:
                raise ValueError(f"Required parameter '{param_name}' is missing")
            
            # Type validation (basic)
            if value is not None:
                expected_type = param_schema.get("type", "string")
                if expected_type == "string" and not isinstance(value, str):
                    value = str(value)
                elif expected_type == "integer" and not isinstance(value, int):
                    try:
                        value = int(value)
                    except ValueError:
                        raise ValueError(f"Parameter '{param_name}' must be an integer")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    try:
                        value = float(value)
                    except ValueError:
                        raise ValueError(f"Parameter '{param_name}' must be a number")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    if isinstance(value, str):
                        value = value.lower() in ("true", "1", "yes", "on")
                    else:
                        value = bool(value)
                
                validated[param_name] = value
        
        return validated
    
    def format_error_response(self, error_message: str) -> Dict[str, Any]:
        """
        Format an error response.
        
        Args:
            error_message: Error message
            
        Returns:
            Formatted error response
        """
        return {
            "success": False,
            "error": error_message,
            "response": f"Sorry, I encountered an error: {error_message}"
        }
    
    def format_success_response(self, result: Any, message: str) -> Dict[str, Any]:
        """
        Format a success response.
        
        Args:
            result: Function result data
            message: Response message
            
        Returns:
            Formatted success response
        """
        return {
            "success": True,
            "result": result,
            "response": message
        }
