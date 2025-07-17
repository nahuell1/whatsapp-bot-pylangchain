"""
Response models for the WhatsApp bot API.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class FunctionResult(BaseModel):
    """Result of a function execution."""
    success: bool = Field(..., description="Whether the function executed successfully")
    result: Any = Field(None, description="Function result data")
    error: Optional[str] = Field(None, description="Error message if function failed")
    execution_time: Optional[float] = Field(None, description="Function execution time in seconds")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "success": True,
                "result": {"temperature": 25, "condition": "sunny"},
                "error": None,
                "execution_time": 1.2
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="System status")
    functions: int = Field(..., description="Number of loaded functions")
    uptime: Optional[float] = Field(None, description="System uptime in seconds")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "functions": 4,
                "uptime": 3600.0
            }
        }


class FunctionDefinition(BaseModel):
    """Function definition for API response."""
    name: str = Field(..., description="Function name")
    description: str = Field(..., description="Function description")
    parameters: Dict[str, Any] = Field(..., description="Function parameters schema")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "name": "weather",
                "description": "Get weather information for a location",
                "parameters": {
                    "location": {
                        "type": "string",
                        "description": "Location to get weather for"
                    }
                }
            }
        }


class FunctionsResponse(BaseModel):
    """Response containing list of available functions."""
    functions: List[FunctionDefinition] = Field(..., description="List of available functions")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "functions": [
                    {
                        "name": "weather",
                        "description": "Get weather information for a location",
                        "parameters": {
                            "location": {
                                "type": "string",
                                "description": "Location to get weather for"
                            }
                        }
                    }
                ]
            }
        }
