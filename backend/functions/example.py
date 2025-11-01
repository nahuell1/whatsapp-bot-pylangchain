"""Example custom function for the WhatsApp bot.

This serves as a template for creating new functions with parameter
validation, error handling, and response formatting.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from functions.base import FunctionBase, bot_function

logger = logging.getLogger(__name__)

DEFAULT_REPEAT_COUNT = 1


@bot_function("example")
class ExampleFunction(FunctionBase):
    """Example function demonstrating the function structure.
    
    Demonstrates parameter validation, message processing, and
    response formatting. Use as template for new functions.
    """
    
    def __init__(self):
        """Initialize the example function with parameters."""
        super().__init__(
            name="example",
            description="Example function that demonstrates the function structure",
            parameters={
                "message": {
                    "type": "string",
                    "description": "Message to echo back",
                    "required": True
                },
                "uppercase": {
                    "type": "boolean",
                    "description": "Whether to return the message in uppercase",
                    "default": False
                },
                "count": {
                    "type": "integer",
                    "description": "Number of times to repeat the message",
                    "default": 1
                }
            },
            intent_examples=[
                {
                    "message": "echo hello world",
                    "parameters": {"message": "hello world"}
                },
                {
                    "message": "repeat TESTING in uppercase 3 times",
                    "parameters": {"message": "TESTING", "uppercase": True, "count": 3}
                }
            ]
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the example function.
        
        Args:
            **kwargs: Function parameters (message, uppercase, count)
            
        Returns:
            Dict with processed message and metadata
        """
        try:
            params = self.validate_parameters(**kwargs)
            message = params["message"]
            uppercase = params.get("uppercase", False)
            count = params.get("count", DEFAULT_REPEAT_COUNT)
            
            logger.info("Executing example function with message: %s", message)
            
            processed_message = message.upper() if uppercase else message
            
            result_messages = []
            for i in range(count):
                result_messages.append(f"{i + 1}. {processed_message}")
            
            result = {
                "original_message": message,
                "processed_message": processed_message,
                "repeated_messages": result_messages,
                "count": count,
                "uppercase": uppercase,
                "timestamp": datetime.now().isoformat()
            }
            
            response_message = self._format_response(result)
            
            return self.format_success_response(result, response_message)
            
        except Exception as e:
            logger.error("Error in example function: %s", str(e))
            return self.format_error_response(str(e))
    
    @staticmethod
    def _format_response(result: Dict[str, Any]) -> str:
        """Format the response message.
        
        Args:
            result: Dict with processed message data
            
        Returns:
            Formatted response message
        """
        response = "📝 **Example Function Result**\n\n"
        
        if result["count"] == 1:
            response += f"Message: {result['processed_message']}"
        else:
            response += f"Repeated {result['count']} times:\n"
            for msg in result["repeated_messages"]:
                response += f"  {msg}\n"
        
        if result["uppercase"]:
            response += "\n🔤 (Converted to uppercase)"
        
        response += f"\n⏰ Processed at: {result['timestamp']}"
        
        return response
