# WhatsApp Bot with LangChain & Function Calling

A professional WhatsApp bot system built with Node.js (whatsapp-web.js) frontend and Python backend using LangChain and GPT-4 for intelligent message processing and function calling.

## Architecture Overview

```
┌─────────────────┐    HTTP     ┌─────────────────┐
│   WhatsApp      │ ──────────> │   Python        │
│   Frontend      │             │   Backend       │
│   (Node.js)     │ <────────── │   (LangChain)   │
└─────────────────┘             └─────────────────┘
                                         │
                                         v
                                ┌─────────────────┐
                                │   Function      │
                                │   Modules       │
                                │   (Plugins)     │
                                └─────────────────┘
```

## Features

- **Intelligent Message Processing**: Uses GPT-4 to detect user intent (function call vs chat)
- **Modular Function System**: Easily add new functions by dropping Python files into the functions folder
- **Professional Architecture**: Clean separation of concerns with proper error handling
- **Configurable**: Environment-based configuration for all components
- **Well Documented**: Comprehensive documentation and type hints
- **Auto-Discovery**: Functions are automatically registered from the functions folder

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.9+
- OpenAI API Key

### Installation

1. Clone the repository
2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Start the backend:
   ```bash
   python backend/main.py
   ```

6. Start the frontend:
   ```bash
   npm start
   ```

## Adding New Functions

To add a new function, create a Python file in the `backend/functions/` directory following this template:

```python
from typing import Dict, Any
from .base import FunctionBase

class MyFunction(FunctionBase):
    def __init__(self):
        super().__init__(
            name="my_function",
            description="Description of what this function does",
            parameters={
                "param1": {
                    "type": "string",
                    "description": "Description of param1"
                }
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        # Your function implementation here
        return {"result": "success", "data": "your_data"}
```

## Configuration

All configuration is done through environment variables in the `.env` file:

- `OPENAI_API_KEY`: Your OpenAI API key
- `BACKEND_HOST`: Backend server host (default: localhost)
- `BACKEND_PORT`: Backend server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)

## Function Examples

The system comes with several example functions:

- **Weather**: Get weather information using OpenMeteo API
- **Home Assistant**: Trigger Home Assistant webhooks
- **IP Camera**: Capture and send IP camera snapshots
- **System Info**: Get system information

## Development

### Project Structure

```
whatsapp-bot-pylangchain/
├── frontend/                 # Node.js WhatsApp frontend
│   ├── src/
│   │   ├── bot.js           # Main WhatsApp bot logic
│   │   ├── api.js           # Backend API communication
│   │   └── utils.js         # Utility functions
│   ├── package.json
│   └── index.js
├── backend/                  # Python backend
│   ├── main.py              # FastAPI application
│   ├── core/                # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py        # Configuration management
│   │   ├── intent_detector.py  # Intent detection with GPT-4
│   │   ├── function_manager.py # Function registration & execution
│   │   └── chat_handler.py  # Chat message handling
│   ├── functions/           # Function modules
│   │   ├── __init__.py
│   │   ├── base.py          # Base function class
│   │   ├── weather.py       # Weather function
│   │   ├── home_assistant.py # Home Assistant function
│   │   ├── ip_camera.py     # IP Camera function
│   │   └── system_info.py   # System info function
│   └── models/              # Data models
│       ├── __init__.py
│       ├── message.py       # Message models
│       └── response.py      # Response models
├── docs/                    # Documentation
├── tests/                   # Test files
├── .env.example            # Environment variables template
├── requirements.txt        # Python dependencies
├── package.json           # Node.js dependencies
└── README.md
```

### Running Tests

```bash
# Python tests
pytest tests/

# Node.js tests
npm test
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
