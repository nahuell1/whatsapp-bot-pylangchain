"""
Basic tests for the WhatsApp bot backend.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from core.config import settings
from core.intent_detector import IntentDetector, IntentResult
from core.function_manager import FunctionManager
from functions.base import FunctionBase


class TestConfig:
    """Test configuration management."""
    
    def test_settings_exist(self):
        """Test that settings are loaded properly."""
        assert hasattr(settings, 'OPENAI_API_KEY')
        assert hasattr(settings, 'BACKEND_HOST')
        assert hasattr(settings, 'BACKEND_PORT')


class TestFunctionBase:
    """Test base function class."""
    
    def test_function_base_initialization(self):
        """Test function base initialization."""
        class TestFunction(FunctionBase):
            def __init__(self):
                super().__init__(
                    name="test",
                    description="Test function",
                    parameters={"param": {"type": "string"}}
                )
            
            async def execute(self, **kwargs):
                return {"success": True}
        
        func = TestFunction()
        assert func.name == "test"
        assert func.description == "Test function"
        assert "param" in func.parameters
    
    def test_parameter_validation(self):
        """Test parameter validation."""
        class TestFunction(FunctionBase):
            def __init__(self):
                super().__init__(
                    name="test",
                    description="Test function",
                    parameters={
                        "required_param": {"type": "string", "required": True},
                        "optional_param": {"type": "integer", "default": 42}
                    }
                )
            
            async def execute(self, **kwargs):
                return {"success": True}
        
        func = TestFunction()
        
        # Test valid parameters
        validated = func.validate_parameters(required_param="test", optional_param=10)
        assert validated["required_param"] == "test"
        assert validated["optional_param"] == 10
        
        # Test missing required parameter
        with pytest.raises(ValueError, match="Required parameter 'required_param' is missing"):
            func.validate_parameters(optional_param=10)


class TestIntentDetector:
    """Test intent detection."""
    
    def test_intent_result_creation(self):
        """Test intent result creation."""
        result = IntentResult(
            intent="function_call",
            function_name="weather",
            parameters={"location": "London"},
            confidence=0.9
        )
        
        assert result.intent == "function_call"
        assert result.function_name == "weather"
        assert result.parameters["location"] == "London"
        assert result.confidence == 0.9
    
    @patch('core.intent_detector.ChatOpenAI')
    def test_intent_detector_initialization(self, mock_chat_openai):
        """Test intent detector initialization."""
        detector = IntentDetector()
        assert detector.llm is not None
        assert "intent detection system" in detector.system_prompt.lower()


class TestFunctionManager:
    """Test function manager."""
    
    def test_function_manager_initialization(self):
        """Test function manager initialization."""
        manager = FunctionManager()
        assert manager.functions == {}
        assert manager.functions_dir is not None
    
    def test_get_function_definitions(self):
        """Test getting function definitions."""
        manager = FunctionManager()
        
        # Create a mock function
        mock_function = Mock()
        mock_function.name = "test_function"
        mock_function.description = "Test function"
        mock_function.parameters = {"param": {"type": "string"}}
        
        manager.functions["test_function"] = mock_function
        
        definitions = manager.get_function_definitions()
        assert len(definitions) == 1
        assert definitions[0]["name"] == "test_function"
        assert definitions[0]["description"] == "Test function"


@pytest.mark.asyncio
class TestAsyncFunctionality:
    """Test async functionality."""
    
    async def test_function_execution_timeout(self):
        """Test function execution with timeout."""
        class SlowFunction(FunctionBase):
            def __init__(self):
                super().__init__(
                    name="slow",
                    description="Slow function",
                    parameters={}
                )
            
            async def execute(self, **kwargs):
                await asyncio.sleep(2)  # Simulate slow operation
                return {"success": True}
        
        manager = FunctionManager()
        slow_func = SlowFunction()
        manager.functions["slow"] = slow_func
        
        # Test with very short timeout
        with patch('core.function_manager.settings.FUNCTION_TIMEOUT', 0.1):
            result = await manager.execute_function("slow", {})
            assert "error" in result
            assert "timed out" in result["error"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
