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
        
        # System prompt for intent detection (will be updated dynamically)
        self.system_prompt = self._build_base_prompt()
    
    def _build_base_prompt(self, functions_text: str = "") -> str:
        """Build the system prompt with optional functions list."""
        base_prompt = f"""Analyze user messages for intent:
- "function_call": execute specific function
- "chat": conversation

{functions_text}

MANDATORY JSON FORMAT:
{{"intent": "function_call"|"chat", "function_name": "exact_function_name", "parameters": {{}}, "confidence": 0.0-1.0}}

⚠️ CRITICAL RULES:
1. intent field: ONLY "function_call" or "chat" - NEVER use function names here
2. function_name field: ONLY exact names from Functions list above
3. parameters field: Use EXACT parameter names from function specifications

For general conversation -> {{"intent":"chat","confidence":0.95}}"""
        
        return base_prompt
    
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
        """Update available functions in system prompt."""
        if not functions:
            self.system_prompt = self._build_base_prompt()
            return
            
        # Create detailed function list with parameters
        func_list = []
        examples_list = []
        
        for name, func in functions.items():
            # Get short description, limit to 50 chars
            desc = func.description[:50] + "..." if len(func.description) > 50 else func.description
            
            # Add parameter information for better inference
            params_info = ""
            if hasattr(func, 'parameters') and func.parameters:
                required_params = []
                optional_params = []
                
                for param_name, param_info in func.parameters.items():
                    param_desc = param_info.get('description', '').split('.')[0]  # First sentence only
                    if param_info.get('required', False):
                        required_params.append(f"{param_name}: {param_desc}")
                    else:
                        optional_params.append(f"{param_name}: {param_desc}")
                
                # Build compact parameter info
                if required_params:
                    params_info = f" (required: {', '.join(required_params)})"
                    if optional_params and len(optional_params) <= 2:  # Limit optional params
                        params_info += f" (optional: {', '.join(optional_params[:2])})"
            
            func_list.append(f"- {name}: {desc}{params_info}")
            
            # Add intent examples if available
            if hasattr(func, 'intent_examples') and func.intent_examples:
                for example in func.intent_examples[:2]:  # Limit to 2 examples per function
                    message = example.get('message', '')
                    parameters = example.get('parameters', {})
                    examples_list.append(f'"{message}" -> {{"intent":"function_call","function_name":"{name}","parameters":{parameters},"confidence":0.9}}')
        
        # Build functions text with examples
        functions_text = f"Functions:\n" + "\n".join(func_list)
        if examples_list:
            functions_text += f"\n\nExamples:\n- " + "\n- ".join(examples_list)
        
        self.system_prompt = self._build_base_prompt(functions_text)
        
        logger.info(f"Updated system prompt with {len(functions)} functions and {len(examples_list)} examples")
