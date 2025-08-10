"""
Chat handler for conversational messages using GPT-4.
"""

import logging
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

from .config import settings

logger = logging.getLogger(__name__)


class ChatHandler:
    """Handles conversational chat messages."""
    
    def __init__(self):
        """Initialize the chat handler."""
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )
        
        # System prompt for chat
        self.system_prompt = """You are a helpful and friendly WhatsApp bot assistant. 
You can help users with various tasks and have conversations with them.

Guidelines:
- Be helpful, friendly, and professional
- Keep responses concise and appropriate for WhatsApp
- If users ask about your capabilities, mention that you can help with weather, home automation, camera snapshots, and system information
- Use emojis appropriately to make conversations more engaging
- You can remember the last 5 interactions with each user
- If you don't know something, admit it honestly
"""
        
        # Store conversation history (simple in-memory storage)
        self.conversation_history: Dict[str, list] = {}
    
    async def handle_chat(self, message: str, user_id: str, memory_store=None) -> str:
        """
        Handle a chat message and return a response.
        
        Args:
            message: User message
            user_id: User identifier
            
        Returns:
            Chat response
        """
        try:
            logger.debug(f"Handling chat message from {user_id}: {message[:100]}...")
            
            # Get or create conversation history for user
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            history = self.conversation_history[user_id]
            
            # Prepare messages for GPT-4
            messages = [SystemMessage(content=self.system_prompt)]
            
            # Add recent conversation history (last 10 messages)
            for msg in history[-10:]:
                messages.append(msg)
            
            # Add current message
            current_message = HumanMessage(content=message)
            messages.append(current_message)
            
            # Get response from GPT-4
            response = await self.llm.agenerate([messages])
            reply = response.generations[0][0].text.strip()
            
            # Update conversation history with correct roles
            history.append(current_message)           # user message
            history.append(AIMessage(content=reply))  # assistant reply
            
            # Keep only last 20 messages to prevent memory issues
            if len(history) > 20:
                history = history[-20:]
                self.conversation_history[user_id] = history
            
            logger.info(f"Chat response generated for {user_id}: {reply[:100]}...")
            return reply
            
        except Exception as e:
            logger.error(f"Error handling chat message: {str(e)}")
            return "Sorry, I encountered an error while processing your message. Please try again."
    
    def clear_history(self, user_id: str):
        """Clear conversation history for a user."""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            logger.info(f"Cleared conversation history for user {user_id}")
    
    def get_history_length(self, user_id: str) -> int:
        """Get the length of conversation history for a user."""
        return len(self.conversation_history.get(user_id, []))

    def record_function_interaction(self, user_id: str, user_message: str, function_name: str, parameters: dict, function_response: str):
        """Record a function call interaction into the conversational history so the model can reference it later.

        We store it as the user's original message followed by an assistant message summarizing the function call result.
        """
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        history = self.conversation_history[user_id]

        summary_header = f"(Function {function_name} executed)"
        if parameters:
            try:
                # Short parameter summary
                parts = []
                for k, v in parameters.items():
                    sval = str(v)
                    if len(sval) > 30:
                        sval = sval[:27] + '...'
                    parts.append(f"{k}={sval}")
                summary_header += " " + ", ".join(parts)
            except Exception:  # pragma: no cover
                pass

        assistant_text = f"{summary_header}" if function_response else summary_header

        history.append(HumanMessage(content=user_message))
        history.append(AIMessage(content=assistant_text))
        # Trim history
        if len(history) > 40:
            self.conversation_history[user_id] = history[-40:]
        logger.debug(f"Recorded function interaction for {user_id}: {function_name}")
