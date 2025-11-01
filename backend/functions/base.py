"""Base class and decorators for bot functions.

This module provides the core functionality for creating and registering
bot functions with automatic discovery and validation.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

logger = logging.getLogger(__name__)

_REGISTERED_FUNCTIONS: Dict[str, Type['FunctionBase']] = {}


def bot_function(name: Optional[str] = None):
    """Decorator to register a class as a bot function.
    
    Enables automatic discovery and registration of bot functions
    while maintaining flexible inheritance patterns.
    
    Args:
        name: Optional function name. If not provided, derives from class name
        
    Returns:
        Decorated class with registration applied
        
    Raises:
        TypeError: If class does not inherit from FunctionBase
        
    Example:
        ```python
        @bot_function("weather")
        class WeatherFunction(FunctionBase):
            pass
        
        @bot_function()
        class CustomBase(FunctionBase):
            pass
            
        @bot_function("camera")  
        class CameraFunction(CustomBase):
            pass
        ```
    """
    def decorator(cls: Type['FunctionBase']) -> Type['FunctionBase']:
        if not issubclass(cls, FunctionBase):
            raise TypeError(
                f"Class {cls.__name__} must inherit from FunctionBase"
            )
        
        function_name = name or cls.__name__.lower().replace('function', '')
        
        _REGISTERED_FUNCTIONS[function_name] = cls
        logger.debug(
            "Registered bot function: %s -> %s",
            function_name,
            cls.__name__
        )
        
        return cls
    return decorator


def get_registered_functions() -> Dict[str, Type['FunctionBase']]:
    """Get all registered bot functions.
    
    Returns:
        Dictionary mapping function names to function classes
    """
    return _REGISTERED_FUNCTIONS.copy()


def clear_function_registry() -> None:
    """Clear the function registry.
    
    Primarily useful for testing to ensure clean state between tests.
    """
    global _REGISTERED_FUNCTIONS
    _REGISTERED_FUNCTIONS.clear()


class FunctionBase(ABC):
    """Abstract base class for all bot functions.
    
    Provides common functionality for parameter validation, error handling,
    and response formatting. All bot functions must inherit from this class.
    
    Attributes:
        name: Unique function identifier
        description: Human-readable function description
        parameters: Schema defining expected parameters
        command_info: Direct command execution metadata
        intent_examples: Training examples for intent detection
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        command_info: Optional[Dict[str, Any]] = None,
        intent_examples: Optional[list] = None
    ):
        """Initialize a bot function.
        
        Args:
            name: Unique function identifier
            description: Human-readable description
            parameters: Parameter schema with types and requirements
            command_info: Optional command execution metadata
            intent_examples: Optional training examples for AI
        """
        self.name = name
        self.description = description
        self.parameters = parameters
        self.command_info = command_info or {}
        self.intent_examples = intent_examples or []
        logger.info("Initialized function: %s", name)
    
    def get_command_metadata(self) -> Dict[str, Any]:
        """Get command metadata for direct execution.
        
        Returns:
            Dictionary containing function metadata, parameters, and examples
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
        """Execute the function with given parameters.
        
        Must be implemented by all subclasses to define function behavior.
        
        Args:
            **kwargs: Function-specific parameters
            
        Returns:
            Dictionary with keys:
                - success (bool): Execution success status
                - result (Any): Function result data
                - response (str): User-facing response message
                - error (str, optional): Error message if failed
        """
        ...
    
    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """Validate and coerce function parameters.
        
        Performs type checking and conversion according to parameter schema.
        
        Args:
            **kwargs: Raw parameters to validate
            
        Returns:
            Dictionary of validated and coerced parameters
            
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        validated = {}
        
        for param_name, param_schema in self.parameters.items():
            value = kwargs.get(param_name)
            
            if param_schema.get("required", False) and value is None:
                raise ValueError(
                    f"Required parameter '{param_name}' is missing"
                )
            
            if value is not None:
                value = self._coerce_parameter_type(
                    param_name,
                    value,
                    param_schema
                )
                validated[param_name] = value
        
        return validated
    
    def _coerce_parameter_type(
        self,
        param_name: str,
        value: Any,
        param_schema: Dict[str, Any]
    ) -> Any:
        """Coerce parameter value to expected type.
        
        Args:
            param_name: Parameter name (for error messages)
            value: Raw parameter value
            param_schema: Parameter schema with type information
            
        Returns:
            Coerced value
            
        Raises:
            ValueError: If value cannot be coerced to expected type
        """
        expected_type = param_schema.get("type", "string")
        
        if expected_type == "string" and not isinstance(value, str):
            return str(value)
        
        if expected_type == "integer" and not isinstance(value, int):
            try:
                return int(value)
            except ValueError:
                raise ValueError(
                    f"Parameter '{param_name}' must be an integer"
                )
        
        if expected_type == "number" and not isinstance(value, (int, float)):
            try:
                return float(value)
            except ValueError:
                raise ValueError(
                    f"Parameter '{param_name}' must be a number"
                )
        
        if expected_type == "boolean" and not isinstance(value, bool):
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            return bool(value)
        
        return value
    
    def format_error_response(self, error_message: str) -> Dict[str, Any]:
        """Format a standardized error response.
        
        Args:
            error_message: Error description
            
        Returns:
            Dictionary with error information
        """
        return {
            "success": False,
            "error": error_message,
            "response": f"Sorry, I encountered an error: {error_message}"
        }
    
    def format_success_response(
        self,
        result: Any,
        message: str
    ) -> Dict[str, Any]:
        """Format a standardized success response.
        
        Args:
            result: Function execution result data
            message: User-facing response message
            
        Returns:
            Dictionary with success information
        """
        return {
            "success": True,
            "result": result,
            "response": message
        }
