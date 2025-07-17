"""
WhatsApp Bot Backend
A FastAPI-based backend for processing WhatsApp messages with LangChain and GPT-4.
"""

import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import settings
from core.intent_detector import IntentDetector
from core.function_manager import FunctionManager
from core.chat_handler import ChatHandler
from models.message import MessageRequest, MessageResponse

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting WhatsApp Bot Backend...")
    
    # Initialize components
    app.state.intent_detector = IntentDetector()
    app.state.function_manager = FunctionManager()
    app.state.chat_handler = ChatHandler()
    
    # Load functions
    await app.state.function_manager.load_functions()
    logger.info(f"Loaded {len(app.state.function_manager.functions)} functions")
    
    yield
    
    # Shutdown
    logger.info("Shutting down WhatsApp Bot Backend...")


# Create FastAPI app
app = FastAPI(
    title="WhatsApp Bot Backend",
    description="Backend API for WhatsApp bot with LangChain and GPT-4",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "WhatsApp Bot Backend is running!"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "functions": len(app.state.function_manager.functions)}


@app.post("/process-message", response_model=MessageResponse)
async def process_message(request: MessageRequest):
    """
    Process a WhatsApp message and return an appropriate response.
    
    Args:
        request: Message request containing user message and metadata
        
    Returns:
        MessageResponse with the bot's response
    """
    try:
        logger.info(f"Processing message: {request.message[:100]}...")
        
        # Detect user intent
        intent_result = await app.state.intent_detector.detect_intent(
            request.message, 
            request.user_id
        )
        
        logger.info(f"Detected intent: {intent_result.intent}")
        
        if intent_result.intent == "function_call":
            # Execute function
            function_result = await app.state.function_manager.execute_function(
                intent_result.function_name,
                intent_result.parameters
            )
            
            response = MessageResponse(
                message=function_result.get("response", "Function executed successfully"),
                intent="function_call",
                function_name=intent_result.function_name,
                metadata=function_result
            )
        else:
            # Handle as chat
            chat_response = await app.state.chat_handler.handle_chat(
                request.message,
                request.user_id
            )
            
            response = MessageResponse(
                message=chat_response,
                intent="chat",
                metadata={}
            )
        
        logger.info(f"Response generated: {response.message[:100]}...")
        return response
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/functions")
async def get_functions():
    """Get list of available functions."""
    return {
        "functions": [
            {
                "name": func.name,
                "description": func.description,
                "parameters": func.parameters
            }
            for func in app.state.function_manager.functions.values()
        ]
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
