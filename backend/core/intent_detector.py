"""Intent detection using GPT-4.

This module determines whether a user message is requesting a function call
or engaging in natural conversation.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI

try:
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:  # pragma: no cover
    from langchain.schema import HumanMessage, SystemMessage

from .config import settings

logger = logging.getLogger(__name__)

INTENT_CHAT = "chat"
INTENT_FUNCTION_CALL = "function_call"


@dataclass
class IntentResult:
    """Result of intent detection analysis.
    
    Attributes:
        intent: Either "function_call" or "chat"
        function_name: Name of detected function (if intent is function_call)
        parameters: Extracted function parameters
        confidence: Confidence score between 0.0 and 1.0
    """
    intent: str
    function_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    confidence: float = 0.0


class IntentDetector:
    """Detects user intent using GPT-4 language model.
    
    Analyzes user messages to determine if they require function execution
    or conversational responses.
    
    Attributes:
        llm: Language model client for intent detection
        system_prompt: Current system prompt with function definitions
    """

    def __init__(self):
        """Initialize the intent detector with LLM client."""
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.1,
            api_key=settings.OPENAI_API_KEY
        )
        self.system_prompt = self._build_base_prompt()
    
    def _build_base_prompt(self, functions_text: str = "") -> str:
        """Build the system prompt with optional functions list.
        
        Args:
            functions_text: Formatted list of available functions and examples
            
        Returns:
            Complete system prompt for intent detection
        """
        base_prompt = f"""Analyze user messages for intent:
- "function_call": execute specific function
- "chat": conversation

{functions_text}

MANDATORY JSON FORMAT:
{{"intent": "function_call"|"chat", "function_name": "exact_function_name", \
"parameters": {{}}, "confidence": 0.0-1.0}}

⚠️ CRITICAL RULES:
1. intent field: ONLY "function_call" or "chat" - NEVER use function names here
2. function_name field: ONLY exact names from Functions list above
3. parameters field: Use EXACT parameter names from function specifications

For general conversation -> {{"intent":"chat","confidence":0.95}}"""
        
        return base_prompt
    
    async def detect_intent(self, message: str, user_id: str) -> IntentResult:
        """Detect user intent from message using GPT-4.
        
        Args:
            message: User message to analyze
            user_id: User identifier (for logging)
            
        Returns:
            IntentResult with detected intent and extracted parameters
        """
        try:
            logger.debug("Detecting intent for message: %s...", message[:100])

            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"User message: {message}")
            ]

            result_text = await self._generate_response_text(messages)
            logger.debug("GPT-4 response: %s", result_text)

            try:
                result_data = json.loads(result_text)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON response: %s", result_text)
                return IntentResult(intent=INTENT_CHAT, confidence=0.5)

            intent_result = self._build_intent_result(result_data)

            logger.info(
                "Intent detected: %s (confidence: %.2f)",
                intent_result.intent,
                intent_result.confidence
            )
            return intent_result
            
        except Exception as e:
            logger.error("Error detecting intent: %s", str(e))
            return IntentResult(intent=INTENT_CHAT, confidence=0.0)
    
    async def update_functions(self, functions: Dict[str, Any]) -> None:
        """Update available functions in system prompt.
        
        Rebuilds the system prompt with current function definitions and examples
        to improve intent detection accuracy.
        
        Args:
            functions: Dictionary of available function instances
        """
        if not functions:
            self.system_prompt = self._build_base_prompt()
            return
        
        func_list = []
        examples_list = []
        
        for name, func in functions.items():
            desc = func.description
            if len(desc) > 50:
                desc = desc[:50] + "..."
            
            params_info = self._build_params_info(func)
            func_list.append(f"- {name}: {desc}{params_info}")
            
            if hasattr(func, 'intent_examples') and func.intent_examples:
                for example in func.intent_examples[:2]:
                    message = example.get('message', '')
                    parameters = example.get('parameters', {})
                    examples_list.append(
                        f'"{message}" -> {{"intent":"{INTENT_FUNCTION_CALL}",'
                        f'"function_name":"{name}","parameters":{parameters},'
                        f'"confidence":0.9}}'
                    )
        
        functions_text = "Functions:\n" + "\n".join(func_list)
        if examples_list:
            functions_text += "\n\nExamples:\n- " + "\n- ".join(examples_list)
        
        self.system_prompt = self._build_base_prompt(functions_text)
        
        logger.info(
            "Updated system prompt with %d functions and %d examples",
            len(functions),
            len(examples_list)
        )
    
    def _build_params_info(self, func: Any) -> str:
        """Build parameter information string for a function.
        
        Args:
            func: Function instance with parameters attribute
            
        Returns:
            Formatted parameter information string
        """
        if not (hasattr(func, 'parameters') and func.parameters):
            return ""
        
        required_params = []
        optional_params = []
        
        for param_name, param_info in func.parameters.items():
            param_desc = param_info.get('description', '').split('.')[0]
            if param_info.get('required', False):
                required_params.append(f"{param_name}: {param_desc}")
            else:
                optional_params.append(f"{param_name}: {param_desc}")
        
        params_info = ""
        if required_params:
            params_info = f" (required: {', '.join(required_params)})"
            if optional_params and len(optional_params) <= 2:
                params_info += f" (optional: {', '.join(optional_params[:2])})"
        
        return params_info

    async def _generate_response_text(self, messages: list) -> str:
        """Call the language model with retries and return raw text."""
        last_error: Optional[Exception] = None
        for attempt in range(1, settings.OPENAI_MAX_RETRIES + 1):
            try:
                logger.debug(f"Intent detector LLM call attempt {attempt}")
                if hasattr(self.llm, "ainvoke"):
                    result = await asyncio.wait_for(
                        self.llm.ainvoke(messages),
                        timeout=settings.OPENAI_TIMEOUT
                    )
                else:  # pragma: no cover - compatibility path
                    chat_result = await asyncio.wait_for(
                        self.llm.agenerate([messages]),
                        timeout=settings.OPENAI_TIMEOUT
                    )
                    return chat_result.generations[0][0].text.strip()

                return self._extract_text_from_response(result)
            except asyncio.TimeoutError as exc:
                last_error = exc
                logger.warning("Intent detector LLM call timed out; retrying...")
            except Exception as exc:  # pragma: no cover - capture unexpected errors
                last_error = exc
                logger.warning(f"Intent detector LLM call failed (attempt {attempt}): {exc}")

        raise last_error or RuntimeError("Intent detector LLM call failed")

    @staticmethod
    def _extract_text_from_response(response: Any) -> str:
        """Normalize text extraction from the LLM response."""
        if response is None:
            return ""

        content = getattr(response, "content", None)
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            return "".join(text_parts).strip()

        # Fallback for legacy ChatResult
        generations = getattr(response, "generations", None)
        if generations:
            try:
                return generations[0][0].text.strip()
            except Exception:  # pragma: no cover
                pass

        return str(response).strip()

    def _build_intent_result(self, data: Dict[str, Any]) -> IntentResult:
        """Validate and convert raw model output into IntentResult.
        
        Args:
            data: Raw JSON data from the model
            
        Returns:
            Validated IntentResult instance
        """
        if not isinstance(data, dict):
            logger.warning("Model returned non-dict payload: %s", data)
            return IntentResult(intent=INTENT_CHAT, confidence=0.3)

        intent = data.get("intent")
        if intent not in {INTENT_CHAT, INTENT_FUNCTION_CALL}:
            logger.warning("Invalid intent value received: %s", intent)
            return IntentResult(intent=INTENT_CHAT, confidence=0.3)

        function_name = (
            data.get("function_name")
            if intent == INTENT_FUNCTION_CALL
            else None
        )
        if intent == INTENT_FUNCTION_CALL and not function_name:
            logger.warning(
                "Function intent without function_name; defaulting to chat"
            )
            return IntentResult(intent=INTENT_CHAT, confidence=0.4)

        parameters = data.get("parameters") or {}
        if not isinstance(parameters, dict):
            logger.warning("Parameters not a dict: %s", parameters)
            parameters = {}

        confidence = data.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            logger.debug("Confidence not numeric: %s", confidence)
            confidence = 0.0

        return IntentResult(
            intent=intent,
            function_name=function_name,
            parameters=parameters,
            confidence=max(0.0, min(confidence, 1.0))
        )
