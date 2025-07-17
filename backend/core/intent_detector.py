"""
Intent detection using GPT-4 to determine if a message is a function call or chat.
"""

import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    """Result of intent detection."""
    intent: str  # "function_call" or "chat"
    function_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    confidence: float = 0.0


class IntentDetector:
    """Detects user intent using GPT-4."""
    
    def __init__(self):
        """Initialize the intent detector."""
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.1,
            api_key=settings.OPENAI_API_KEY
        )
        
        # System prompt for intent detection
        self.system_prompt = """You are an intent detection system for a WhatsApp bot. 
Your task is to analyze user messages and determine if they are:
1. "function_call" - User wants to execute a specific function
2. "chat" - User wants to have a conversation

Available functions:
- weather: Get weather information for a location
- home_assistant: Trigger Home Assistant automations/actions
- ip_camera: Get camera snapshots
- system_info: Get system information
- news: Get latest news from Reddit Argentina (no parameters needed)

For function calls, extract the function name and parameters.

Respond with a JSON object containing:
{
    "intent": "function_call" or "chat",
    "function_name": "function_name" (if intent is function_call),
    "parameters": {...} (if intent is function_call),
    "confidence": 0.0-1.0
}

Examples:
- "What's the weather like?" -> {"intent": "function_call", "function_name": "weather", "parameters": {"location": "user_location"}, "confidence": 0.9}
- "Hello, how are you?" -> {"intent": "chat", "confidence": 0.95}
- "Turn on the lights" -> {"intent": "function_call", "function_name": "home_assistant", "parameters": {"action": "turn_on_lights"}, "confidence": 0.85}
- "Dame las últimas noticias" -> {"intent": "function_call", "function_name": "news", "parameters": {}, "confidence": 0.9}
- "Qué está pasando en Argentina?" -> {"intent": "function_call", "function_name": "news", "parameters": {}, "confidence": 0.8}
"""
    
    async def detect_intent(self, message: str, user_id: str) -> IntentResult:
        """
        Detect user intent from message.
        
        Args:
            message: User message
            user_id: User identifier
            
        Returns:
            IntentResult with detected intent and parameters
        """
        try:
            logger.debug(f"Detecting intent for message: {message[:100]}...")
            
            # Prepare messages for GPT-4
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"User message: {message}")
            ]
            
            # Get response from GPT-4
            response = await self.llm.agenerate([messages])
            result_text = response.generations[0][0].text.strip()
            
            logger.debug(f"GPT-4 response: {result_text}")
            
            # Parse JSON response
            try:
                result_data = json.loads(result_text)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON response: {result_text}")
                # Fallback to chat intent
                return IntentResult(intent="chat", confidence=0.5)
            
            # Create IntentResult
            intent_result = IntentResult(
                intent=result_data.get("intent", "chat"),
                function_name=result_data.get("function_name"),
                parameters=result_data.get("parameters", {}),
                confidence=result_data.get("confidence", 0.0)
            )
            
            logger.info(f"Intent detected: {intent_result.intent} (confidence: {intent_result.confidence})")
            return intent_result
            
        except Exception as e:
            logger.error(f"Error detecting intent: {str(e)}")
            # Fallback to chat intent on error
            return IntentResult(intent="chat", confidence=0.0)
    
    async def update_functions(self, functions: Dict[str, Any]):
        """
        Update the available functions in the system prompt.
        
        Args:
            functions: Dictionary of available functions
        """
        function_descriptions = []
        for name, func in functions.items():
            function_descriptions.append(f"- {name}: {func.description}")
        
        functions_text = "\n".join(function_descriptions)
        
        self.system_prompt = f"""You are an intent detection system for a WhatsApp bot. 
Your task is to analyze user messages and determine if they are:
1. "function_call" - User wants to execute a specific function
2. "chat" - User wants to have a conversation

Available functions:
{functions_text}

For function calls, extract the function name and parameters.

Respond with a JSON object containing:
{{
    "intent": "function_call" or "chat",
    "function_name": "function_name" (if intent is function_call),
    "parameters": {{...}} (if intent is function_call),
    "confidence": 0.0-1.0
}}

Examples:
- "What's the weather like?" -> {{"intent": "function_call", "function_name": "weather", "parameters": {{"location": "user_location"}}, "confidence": 0.9}}
- "Hello, how are you?" -> {{"intent": "chat", "confidence": 0.95}}
- "Turn on the lights" -> {{"intent": "function_call", "function_name": "home_assistant", "parameters": {{"action": "turn_on_lights"}}, "confidence": 0.85}}
"""
        
        logger.info("Updated system prompt with new functions")
