"""
Message models for the WhatsApp bot API.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    """Request model for processing messages."""
    message: str = Field(..., description="The message content")
    user_id: str = Field(..., description="Unique identifier for the user")
    chat_id: str = Field(..., description="Unique identifier for the chat")
    timestamp: Optional[str] = Field(None, description="Message timestamp")
    message_type: Optional[str] = Field("text", description="Type of message (text, image, etc.)")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "message": "What's the weather like today?",
                "user_id": "user123",
                "chat_id": "chat456",
                "timestamp": "2023-12-01T10:00:00Z",
                "message_type": "text"
            }
        }


class MessageResponse(BaseModel):
    """Response model for processed messages."""
    message: str = Field(..., description="The bot's response message")
    intent: str = Field(..., description="Detected intent (chat or function_call)")
    function_name: Optional[str] = Field(None, description="Name of executed function (if any)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "message": "The weather today is sunny with a high of 25°C",
                "intent": "function_call",
                "function_name": "weather",
                "metadata": {
                    "location": "New York",
                    "temperature": 25,
                    "condition": "sunny"
                }
            }
        }
