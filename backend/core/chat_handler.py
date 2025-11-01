"""Chat handler for conversational messages using GPT-4.

This module handles natural language conversations with users,
maintaining conversation history and providing context-aware responses.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI

try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
except ImportError:  # pragma: no cover
    from langchain.schema import AIMessage, HumanMessage, SystemMessage

from .config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful and friendly WhatsApp bot assistant.
You can help users with various tasks and have conversations with them.

Guidelines:
- Be helpful, friendly, and professional
- Keep responses concise and appropriate for WhatsApp
- If users ask about your capabilities, mention that you can help with weather, \
home automation, camera snapshots, and system information
- Use emojis appropriately to make conversations more engaging
- You can remember the last 5 interactions with each user
- If you don't know something, admit it honestly
"""

MAX_CONVERSATION_HISTORY = 20
CONTEXT_WINDOW_SIZE = 10


class ChatHandler:
    """Handles conversational chat messages with context awareness.
    
    Attributes:
        llm: Language model client for generating responses
        system_prompt: Base system prompt for conversations
        conversation_history: Per-user conversation history storage
    """
    
    def __init__(self):
        """Initialize the chat handler with LLM client."""
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )
        self.system_prompt = SYSTEM_PROMPT
        self.conversation_history: Dict[str, List[Any]] = {}
    
    async def handle_chat(
        self,
        message: str,
        user_id: str,
        memory_store=None
    ) -> str:
        """Handle a chat message and return a response.
        
        Args:
            message: User message to process
            user_id: Unique identifier for the user
            memory_store: Optional memory store for conversation persistence
            
        Returns:
            Generated chat response
        """
        try:
            logger.debug(
                "Handling chat message from %s: %s...",
                user_id,
                message[:100]
            )
            
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            history = self.conversation_history[user_id]
            
            messages: List[Any] = [SystemMessage(content=self.system_prompt)]
            messages.extend(history[-CONTEXT_WINDOW_SIZE:])
            
            current_message = HumanMessage(content=message)
            messages.append(current_message)
            
            reply = await self._generate_chat_reply(messages)
            
            history.append(current_message)
            history.append(AIMessage(content=reply))
            
            if len(history) > MAX_CONVERSATION_HISTORY:
                self.conversation_history[user_id] = history[-MAX_CONVERSATION_HISTORY:]
            
            logger.info(
                "Chat response generated for %s: %s...",
                user_id,
                reply[:100]
            )
            return reply
            
        except Exception as e:
            logger.error("Error handling chat message: %s", str(e))
            return (
                "Sorry, I encountered an error while processing your message. "
                "Please try again."
            )
    
    def clear_history(self, user_id: str) -> None:
        """Clear conversation history for a specific user.
        
        Args:
            user_id: User identifier whose history should be cleared
        """
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            logger.info("Cleared conversation history for user %s", user_id)
    
    def get_history_length(self, user_id: str) -> int:
        """Get the number of messages in user's conversation history.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of messages in history
        """
        return len(self.conversation_history.get(user_id, []))

    def record_function_interaction(
        self,
        user_id: str,
        user_message: str,
        function_name: str,
        parameters: Dict[str, Any],
        function_response: str
    ) -> None:
        """Record a function call in conversation history for context.
        
        Stores the user's original message and a summary of the function
        execution to maintain conversational context.
        
        Args:
            user_id: User identifier
            user_message: Original user message that triggered the function
            function_name: Name of the executed function
            parameters: Function parameters used
            function_response: Response from the function
        """
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        history = self.conversation_history[user_id]
        
        summary_header = f"(Function {function_name} executed)"
        if parameters:
            try:
                param_parts = []
                for key, value in parameters.items():
                    str_val = str(value)
                    if len(str_val) > 30:
                        str_val = str_val[:27] + '...'
                    param_parts.append(f"{key}={str_val}")
                summary_header += " " + ", ".join(param_parts)
            except Exception:  # pragma: no cover
                pass
        
        assistant_text = summary_header if function_response else summary_header
        
        history.append(HumanMessage(content=user_message))
        history.append(AIMessage(content=assistant_text))
        
        if len(history) > MAX_CONVERSATION_HISTORY * 2:
            self.conversation_history[user_id] = history[-(MAX_CONVERSATION_HISTORY * 2):]
        
        logger.debug(
            "Recorded function interaction for %s: %s",
            user_id,
            function_name
        )

    async def _generate_chat_reply(self, messages: list) -> str:
        """Call the language model with retries to obtain a reply."""
        last_error: Optional[Exception] = None
        for attempt in range(1, settings.OPENAI_MAX_RETRIES + 1):
            try:
                logger.debug(f"Chat handler LLM call attempt {attempt}")
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
                logger.warning("Chat handler LLM call timed out; retrying...")
            except Exception as exc:  # pragma: no cover - guard unexpected errors
                last_error = exc
                logger.warning(f"Chat handler LLM call failed (attempt {attempt}): {exc}")

        raise last_error or RuntimeError("Chat handler LLM call failed")

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

        generations = getattr(response, "generations", None)
        if generations:
            try:
                return generations[0][0].text.strip()
            except Exception:  # pragma: no cover
                pass

        return str(response).strip()
