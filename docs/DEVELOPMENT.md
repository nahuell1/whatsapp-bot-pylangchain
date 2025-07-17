# Developer Documentation

This document provides detailed information for developers working on the WhatsApp Bot project.

## Architecture Overview

The WhatsApp Bot consists of two main components:

1. **Frontend (Node.js)**: Handles WhatsApp Web.js communication
2. **Backend (Python)**: Processes messages using LangChain and GPT-4

### Communication Flow

```
WhatsApp → Frontend → Backend → LangChain → GPT-4 → Functions → Response
```

## Frontend (Node.js)

### Key Components

- **index.js**: Main entry point, initializes WhatsApp client
- **src/bot.js**: Main bot logic, handles message processing
- **src/message-processor.js**: Extracts and preprocesses messages
- **src/config.js**: Configuration management
- **src/utils/logger.js**: Logging utility

### Message Processing Flow

1. Message received from WhatsApp
2. Extract message information (user, text, type)
3. Send to Python backend via HTTP
4. Receive response from backend
5. Format and send response back to WhatsApp

## Backend (Python)

### Key Components

- **main.py**: FastAPI application entry point
- **core/**: Core functionality modules
  - **config.py**: Configuration management
  - **intent_detector.py**: Intent detection using GPT-4
  - **function_manager.py**: Function loading and execution
  - **chat_handler.py**: Chat message handling
- **functions/**: Function modules
  - **base.py**: Base class for all functions
  - **weather.py**: Weather information function
  - **home_assistant.py**: Home Assistant integration
  - **ip_camera.py**: IP camera snapshots
  - **system_info.py**: System information
- **models/**: Data models for API

### Intent Detection

The system uses GPT-4 to analyze incoming messages and determine if they are:
- **Function calls**: Specific tasks to execute
- **Chat messages**: General conversation

### Function System

Functions are automatically loaded from the `backend/functions/` directory. Each function:
- Inherits from `FunctionBase`
- Defines parameters and description
- Implements the `execute` method
- Returns structured responses

## Adding New Functions

### Step 1: Create Function File

Create a new Python file in `backend/functions/`:

```python
from typing import Dict, Any
from .base import FunctionBase

class MyNewFunction(FunctionBase):
    def __init__(self):
        super().__init__(
            name="my_function",
            description="Description of what this function does",
            parameters={
                "param1": {
                    "type": "string",
                    "description": "Parameter description",
                    "required": True
                },
                "param2": {
                    "type": "integer",
                    "description": "Another parameter",
                    "default": 10
                }
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            # Validate parameters
            params = self.validate_parameters(**kwargs)
            
            # Your function logic here
            result = {"status": "success", "data": "your_data"}
            
            # Format response
            response_message = f"Function executed successfully: {result}"
            
            return self.format_success_response(result, response_message)
            
        except Exception as e:
            return self.format_error_response(str(e))
```

### Step 2: Restart Backend

The function will be automatically loaded when the backend starts.

### Step 3: Update Intent Detection (Optional)

If your function needs special intent detection, you can modify the system prompt in `core/intent_detector.py`.

## Configuration

### Environment Variables

All configuration is done through environment variables in the `.env` file:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-nano-2025-04-14

# Backend Configuration
BACKEND_HOST=localhost
BACKEND_PORT=8000

# Function-specific Configuration
HOME_ASSISTANT_URL=http://your-ha-instance:8123
HOME_ASSISTANT_TOKEN=your_token
```

### Backend Configuration

The backend uses Pydantic for configuration management in `core/config.py`. Add new configuration options there.

### Frontend Configuration

The frontend configuration is in `src/config.js`. Add new options there.

## Testing

### Running Tests

```bash
# Python tests
source venv/bin/activate
pytest tests/

# Node.js tests
npm test
```

### Test Structure

- `tests/test_backend.py`: Backend functionality tests
- `tests/test_functions.py`: Function tests
- `tests/test_frontend.js`: Frontend tests

## Debugging

### Logging

Both frontend and backend have comprehensive logging:

- **Frontend**: Logs to console and `logs/whatsapp-bot.log`
- **Backend**: Uses Python logging, configurable via `LOG_LEVEL`

### Common Issues

1. **Backend Connection**: Check `BACKEND_URL` in frontend config
2. **Function Loading**: Check function file structure and imports
3. **WhatsApp Authentication**: Delete `.wwebjs_auth` folder to re-authenticate

## API Reference

### Backend Endpoints

- `POST /process-message`: Process WhatsApp message
- `GET /functions`: Get available functions
- `GET /health`: Health check

### Message Request Format

```json
{
    "message": "User message text",
    "user_id": "user_identifier",
    "chat_id": "chat_identifier",
    "timestamp": "2023-12-01T10:00:00Z",
    "message_type": "text"
}
```

### Message Response Format

```json
{
    "message": "Bot response",
    "intent": "function_call",
    "function_name": "weather",
    "metadata": {
        "additional": "data"
    }
}
```

## Development Workflow

1. **Make changes** to code
2. **Test locally** with development setup
3. **Run tests** to ensure nothing breaks
4. **Update documentation** if needed
5. **Commit changes** with descriptive messages

## Best Practices

### Code Style

- **Python**: Follow PEP 8, use type hints
- **JavaScript**: Use ESLint configuration
- **Documentation**: Use docstrings and comments

### Error Handling

- Always wrap function execution in try-catch blocks
- Return structured error responses
- Log errors with appropriate detail

### Security

- Never commit API keys or sensitive data
- Use environment variables for configuration
- Validate all user inputs
- Sanitize outputs before sending to WhatsApp

## Performance Considerations

- Use async/await for I/O operations
- Implement proper timeout handling
- Cache frequently accessed data
- Monitor memory usage for long-running processes

## Deployment

### Production Setup

1. Use production-grade WSGI server (e.g., Gunicorn)
2. Set up reverse proxy (e.g., Nginx)
3. Configure proper logging and monitoring
4. Use environment-specific configuration
5. Set up automated backups

### Environment Setup

```bash
# Production environment
export OPENAI_API_KEY=your_production_key
export LOG_LEVEL=INFO
export BACKEND_PORT=8000
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Update documentation
6. Submit a pull request

## Troubleshooting

### Common Problems

1. **Module not found errors**: Check Python path and imports
2. **WhatsApp disconnects**: Check network connectivity and authentication
3. **Function execution errors**: Check function parameters and validation
4. **Backend timeout**: Increase timeout settings or optimize function performance

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Frontend
export LOG_LEVEL=debug

# Backend
export LOG_LEVEL=DEBUG
```

## Future Enhancements

- Voice message processing
- Image recognition integration
- Multi-language support
- Advanced conversation memory
- Function scheduling
- Analytics and reporting
