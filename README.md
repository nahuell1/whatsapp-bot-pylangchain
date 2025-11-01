# WhatsApp Bot with AI Intent Detection & Dynamic Functions

A WhatsApp bot system with intelligent message processing, featuring **GPT-powered intent detection**, **automatic function discovery**, and **multi-camera support**. Built with Node.js frontend (whatsapp-web.js) and Python backend using LangChain and OpenAI GPT.

## 🚀 Key Features

### 🧠 Intelligent AI Processing
- **Dynamic Intent Detection**: Uses GPT to automatically detect user intent and function calls from natural language
- **Smart Parameter Inference**: Automatically extracts and validates function parameters from conversational messages
- **Context-Aware Responses**: Maintains conversation history and provides intelligent, contextual replies
- **Conversation Memory**: Persistent chat history with Redis or in-memory storage

### 🔧 Automatic Function Discovery
- **Zero Configuration**: Drop Python functions into `/backend/functions/` and they're automatically available
- **Dynamic Examples**: Functions include training examples for better AI understanding
- **Hot Reloading**: Functions are loaded dynamically without restart
- **Decorator-Based**: Simple `@bot_function()` decorator for instant registration

### 📸 Advanced Camera System
- **Multi-Protocol Support**: RTSP, HTTP, ONVIF, and MJPEG cameras
- **Automatic Discovery**: Environment-based camera configuration with auto-detection
- **Concurrent Capture**: Capture from multiple cameras simultaneously (configurable limit)
- **Base64 Image Transmission**: Seamless image sharing through WhatsApp
- **Caching**: Image caching to reduce redundant captures

### 🏠 Smart Home Integration
- **Home Assistant Support**: Full integration with Home Assistant automation
- **Entity Control**: Turn on/off lights, scenes, automations, switches, and more
- **State Monitoring**: Check sensor states and device information
- **Device Discovery**: List all available entities and their states

### 🌍 Rich Function Library
- **Weather Information**: Real-time weather and 7-day forecasts (OpenMeteo API)
- **News Updates**: Latest news from Reddit Argentina
- **System Monitoring**: CPU, memory, disk usage, process info, and system statistics
- **Dollar Exchange**: Argentine peso/USD exchange rates (official, blue, MEP)
- **Wikipedia Search**: Multi-language Wikipedia article search with intelligent scoring
- **Trends**: X/Twitter trending topics with fallback strategies
- **Google Calendar**: OAuth integration for calendar event management

## 📋 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        WhatsApp Message                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                ┌──────────────────────────────┐
                │    Node.js Frontend          │
                │  (whatsapp-web.js)           │
                └──────────────┬───────────────┘
                               │
                      ┌────────┴────────┐
                      │   Message Type? │
                      └────────┬────────┘
                               │
               ┌───────────────┴───────────────┐
               │                               │
               ▼                               ▼
    ┌──────────────────┐           ┌──────────────────┐
    │ Direct Command   │           │ Natural Language │
    │   (!command)     │           │    Processing    │
    └─────────┬────────┘           └─────────┬────────┘
              │                              │
              │                              ▼
              │                    ┌──────────────────┐
              │                    │ Python Backend   │
              │                    │   (FastAPI)      │
              │                    └─────────┬────────┘
              │                              │
              │                              ▼
              │                    ┌──────────────────┐
              │                    │ GPT Intent       │
              │                    │   Detector       │
              │                    └─────────┬────────┘
              │                              │
              │                              ▼
              │                    ┌──────────────────┐
              │                    │ Function Manager │
              │                    │ (Dynamic Load)   │
              │                    └─────────┬────────┘
              │                              │
              └───────────────┬──────────────┘
                              │
                              ▼
                   ┌──────────────────┐
                   │ Function Execute │
                   │  (Validation +   │
                   │   Execution)     │
                   └─────────┬────────┘
                             │
                             ▼
                  ┌──────────────────┐
                  │ Response Process │
                  │ (Text + Media)   │
                  └─────────┬────────┘
                            │
                            ▼
                 ┌──────────────────┐
                 │ WhatsApp Response│
                 │ (with images)    │
                 └──────────────────┘
```

## 🛠 Installation

### Prerequisites
- **Node.js** 18+ with npm
- **Python** 3.9+ (3.12 recommended)
- **OpenAI API Key** (GPT access required)
- **Redis** (optional, for persistent conversation memory)

### Quick Setup

1. **Clone Repository**:
```bash
git clone https://github.com/nahuell1/whatsapp-bot-pylangchain.git
cd whatsapp-bot-pylangchain
```

2. **Run Setup Script**:
```bash
chmod +x setup.sh start.sh
./setup.sh
```
This will:
- Install Node.js dependencies
- Create Python virtual environment
- Install Python dependencies
- Create `.env` file from template

3. **Configure Environment**:
```bash
cp .env.example .env
nano .env
# Required: Set OPENAI_API_KEY
# Optional: Configure cameras, Home Assistant, etc.
```

**Minimum Configuration**:
```bash
OPENAI_API_KEY=sk-your-api-key-here
```

4. **Start the Bot**:
```bash
./start.sh
```

5. **Authenticate WhatsApp**:
- Scan QR code with WhatsApp mobile app when prompted
- Wait for "WhatsApp client is ready!" message

That's it! The bot is now running and ready to receive messages. 🎉

## 🛠 Docker compose

### Prerequisites
- **OpenAI API Key** (GPT access required)
- **Docker** and **Docker Compose** installed

### Quick Setup and Run

1. **Clone Repository**:
```bash
git clone https://github.com/nahuell1/whatsapp-bot-pylangchain.git
cd whatsapp-bot-pylangchain
```

2. **Create .env File**:
```bash
cp .env.example .env
nano .env
# Required: Set OPENAI_API_KEY
# Optional: Configure cameras, Home Assistant, etc.
```

3. **Start Services**:
```bash
docker-compose up -d
```

4. **Authenticate WhatsApp**:
- Check logs for QR code URL:
```bash
docker-compose logs -f whatsapp-bot
```

5. **Authenticate WhatsApp**:
- Scan QR code with WhatsApp mobile app when prompted
- Wait for "WhatsApp client is ready!" message

That's it! The bot is now running and ready to receive messages. 🎉

## 📱 Usage Examples

### Natural Language Processing
The bot understands natural language and automatically detects intent:

```
User: "What's the weather like in Buenos Aires?"
Bot: 🌍 Weather for Buenos Aires
     🌡️ Current: 22°C
     ☀️ Clear sky
```

```
User: "turn on the office lights"  
Bot: 🏠 Office has been turned on successfully!
```

```
User: "show me all cameras"
Bot: 📸 Capture Multiple Cameras
     ✅ Successful: 2
     📱 Total: 2
     [Sends images from all cameras]
```

### Direct Commands
For immediate execution without AI processing:

```
!weather Buenos Aires         # Weather information
!allcameras                   # All camera snapshots
!camera kitchen               # Specific camera
!dollar                       # Exchange rates
!news                         # Latest news
!system_info                  # System status
!help                         # Available commands
```

## 🔧 Adding New Functions

### Simple Function Example
Create `/backend/functions/my_function.py`:

```python
from functions.base import FunctionBase, bot_function
from typing import Dict, Any

@bot_function("my_function")
class MyFunction(FunctionBase):
    def __init__(self):
        super().__init__(
            name="my_function",
            description="Description of what this function does",
            parameters={
                "message": {
                    "type": "string", 
                    "description": "Input message",
                    "required": True
                },
                "count": {
                    "type": "integer",
                    "description": "Number of repetitions", 
                    "required": False,
                    "default": 1
                }
            },
            # Examples for AI training
            intent_examples=[
                {
                    "message": "repeat hello 3 times",
                    "parameters": {"message": "hello", "count": 3}
                },
                {
                    "message": "echo good morning",
                    "parameters": {"message": "good morning"}
                }
            ]
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        params = self.validate_parameters(**kwargs)
        message = params["message"]
        count = params.get("count", 1)
        
        result = (message + " ") * count
        
        return self.format_success_response(
            {"repeated_message": result},
            f"Repeated '{message}' {count} time(s): {result}"
        )
```

**That's it!** Restart the bot and your function is automatically:
- 🔄 Loaded and registered
- 🧠 Available for AI intent detection  
- 📖 Trained with your examples
- 💬 Ready for natural language queries

### Advanced Features

#### Camera Function Example
```python
@bot_function("security_camera")
class SecurityCameraFunction(FunctionBase):
    def __init__(self):
        super().__init__(
            name="security_camera",
            description="Capture snapshots from security cameras with motion detection",
            parameters={
                "location": {
                    "type": "string",
                    "description": "Camera location (front, back, garage)",
                    "required": True
                },
                "motion_detect": {
                    "type": "boolean", 
                    "description": "Enable motion detection",
                    "required": False,
                    "default": False
                }
            },
            intent_examples=[
                {
                    "message": "check the front door camera",
                    "parameters": {"location": "front"}
                },
                {
                    "message": "security check with motion detection",
                    "parameters": {"location": "all", "motion_detect": True}
                }
            ]
        )
        
    async def execute(self, **kwargs) -> Dict[str, Any]:
        # Your implementation here
        # Return format_success_response() with image data
        pass
```

## 📊 Available Functions

| Function | Description | Natural Language Examples |
|----------|-------------|---------------------------|
| **🌤 Weather** | Weather information via OpenMeteo | "weather in Madrid", "forecast for tomorrow" |
| **🏠 Home Assistant** | Smart home device control | "turn on bedroom lights", "check temperature" |
| **📷 Camera** | Single camera snapshot | "show front door", "kitchen camera" |
| **📸 AllCameras** | Multi-camera simultaneous capture | "show all cameras", "security check" |
| **💵 Dollar** | Argentine peso exchange rates | "dollar price", "current exchange rate" |
| **📰 News** | Latest Argentina news from Reddit | "latest news", "what's happening" |
| **💻 System Info** | Server monitoring and stats | "system status", "check CPU usage" |

## ⚙️ Configuration

### Core Settings (.env)
```bash
# ========== Required ==========
OPENAI_API_KEY=sk-your-api-key-here

# ========== Backend ==========
BACKEND_URL=http://localhost:8000
BACKEND_HOST=localhost
BACKEND_PORT=8000
OPENAI_MODEL=gpt-4-turbo-preview

# ========== Logging ==========
LOG_LEVEL=INFO

# ========== Features ==========
ENABLE_GROUP_MESSAGES=true
ENABLE_TYPING_INDICATOR=true
MAX_MESSAGE_LENGTH=10000

# ========== Memory ==========
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
# Leave REDIS_* empty to use in-memory storage

# ========== Timeouts ==========
FUNCTION_TIMEOUT=30
BACKEND_TIMEOUT=30000
```

### Camera Configuration
```bash
# HTTP Camera Example
CAMERA_KITCHEN_IP=192.168.1.100
CAMERA_KITCHEN_TYPE=http
CAMERA_KITCHEN_PATH=/snapshot.jpg
CAMERA_KITCHEN_USERNAME=admin
CAMERA_KITCHEN_PASSWORD=secretpass

# RTSP Camera Example
CAMERA_FRONTDOOR_IP=192.168.1.101
CAMERA_FRONTDOOR_TYPE=rtsp
CAMERA_FRONTDOOR_URL=rtsp://admin:pass@192.168.1.101/stream1

# ONVIF Camera Example
CAMERA_GARAGE_IP=192.168.1.102
CAMERA_GARAGE_TYPE=onvif
CAMERA_GARAGE_USERNAME=admin
CAMERA_GARAGE_PASSWORD=pass

# MJPEG Camera Example
CAMERA_BACKYARD_IP=192.168.1.103
CAMERA_BACKYARD_TYPE=mjpeg
CAMERA_BACKYARD_PATH=/mjpeg
CAMERA_BACKYARD_USERNAME=admin
CAMERA_BACKYARD_PASSWORD=pass
```

### Home Assistant Integration
```bash
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HOME_ASSISTANT_TOKEN=your_long_lived_access_token_here

# To get token:
# 1. Go to Home Assistant Profile
# 2. Scroll to "Long-Lived Access Tokens"
# 3. Click "Create Token"
```

### Google Calendar Integration
```bash
GOOGLE_CALENDAR_CLIENT_ID=your_client_id
GOOGLE_CALENDAR_CLIENT_SECRET=your_client_secret
GOOGLE_CALENDAR_PRIMARY=your_primary_calendar_id

# Setup instructions in backend/functions/google_calendar.py
```

### Access Control
```bash
# Comma-separated phone numbers (without @c.us)
# Leave empty to allow all users
ALLOWED_USER_IDS=5491112345678,5491187654321
```

## 🚀 Advanced Usage

### Management Commands
```bash
./start.sh                    # Start the bot
./start.sh stop               # Stop the bot  
./start.sh restart            # Restart with new changes
./start.sh status             # Check status
./start.sh logs               # View recent logs
./start.sh logs -f            # Follow logs in real-time
```

### Debug Mode
```bash
echo "LOG_LEVEL=DEBUG" >> .env
./start.sh restart
./start.sh logs -f            # Watch detailed logs
```

### Testing Functions
```bash
# Test backend directly
curl -X POST http://localhost:8000/process-message \\
  -H "Content-Type: application/json" \\
  -d '{"message": "show me all cameras", "user_id": "test"}'

# List available functions  
curl http://localhost:8000/functions
```

## 🏗 Architecture Details

### Intent Detection System
- **GPT Powered**: Uses advanced language model for intent classification and parameter extraction
- **Dynamic Training**: Functions provide examples that automatically update AI prompts
- **Parameter Extraction**: Intelligent extraction and type coercion of function parameters from natural language
- **Confidence Scoring**: Each detection includes confidence levels and metadata
- **Fallback Handling**: Graceful degradation when intent cannot be determined

### Function Management
- **Auto-Discovery**: Functions are automatically loaded from the `/backend/functions/` directory
- **Decorator-Based**: Simple `@bot_function("name")` decorator for instant registration
- **Inheritance System**: Base class (`FunctionBase`) provides common functionality and validation
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Timeout Protection**: Configurable timeout for function execution
- **Type Validation**: Automatic parameter type validation and coercion

### Message Processing Pipeline
1. **Message Reception** (WhatsApp → Node.js via whatsapp-web.js)
2. **Deduplication** (Check processed message IDs to avoid duplicates)
3. **Access Control** (Verify user is authorized if ALLOWED_USER_IDS is set)
4. **Command Detection** (Direct `!command` vs Natural Language)
5. **Intent Analysis** (GPT classification with function examples)
6. **Parameter Validation** (Type checking and required field validation)
7. **Function Execution** (Execute with timeout protection)
8. **Response Formatting** (Text + Media handling with Base64 images)
9. **Delivery** (WhatsApp response with proper error handling)

### Conversation Memory
- **Persistent Storage**: Redis-based or in-memory conversation history
- **Context Window**: Configurable conversation history (default: 10 messages)
- **User Isolation**: Each user has separate conversation context
- **Expiration**: Automatic cleanup of old conversations (default: 24 hours)

## 🧪 Development

### Project Structure
```
whatsapp-bot-pylangchain/
├── index.js                 # Main entry point
├── src/                     # Node.js Frontend
│   ├── bot.js              # Main WhatsApp bot logic
│   ├── command-handler.js  # Direct command processing
│   ├── message-processor.js # Message parsing utilities
│   ├── config.js           # Frontend configuration
│   └── utils/
│       └── logger.js       # Custom logger
├── backend/                # Python Backend
│   ├── main.py            # FastAPI application
│   ├── core/              # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py      # Configuration management (Pydantic)
│   │   ├── chat_handler.py    # GPT conversation handler
│   │   ├── intent_detector.py # Intent detection & classification
│   │   ├── function_manager.py # Dynamic function loading
│   │   └── memory.py      # Conversation memory (Redis/in-memory)
│   ├── functions/         # Function modules (auto-loaded)
│   │   ├── __init__.py
│   │   ├── base.py        # Base class for all functions
│   │   ├── camera.py      # Single camera capture
│   │   ├── allcameras.py  # Multi-camera concurrent capture
│   │   ├── ip_camera.py   # Simple IP camera
│   │   ├── weather.py     # Weather via OpenMeteo
│   │   ├── home_assistant.py # Home Assistant integration
│   │   ├── google_calendar.py # Google Calendar OAuth
│   │   ├── dollar.py      # Exchange rates
│   │   ├── news.py        # Reddit RSS news
│   │   ├── trends.py      # X/Twitter trends
│   │   ├── wiki.py        # Wikipedia search
│   │   ├── system_info.py # System monitoring
│   │   └── example.py     # Template/example function
│   └── models/            # Pydantic models
│       ├── __init__.py
│       ├── message.py     # Message request/response models
│       └── response.py    # Response models
├── tests/                 # Test files
│   └── test_backend.py
├── docs/                  # Documentation
│   └── DEVELOPMENT.md
├── setup.sh              # Setup script
├── start.sh              # Start/stop script
├── requirements.txt      # Python dependencies
└── package.json          # Node.js dependencies
```

### Running Tests
```bash
# Python backend tests
cd backend
python -m pytest tests/ -v

# Check Python code quality
cd backend
python -m pylint core/ functions/

# Node.js tests (if implemented)
npm test
```

### Creating New Functions

All functions must:
- Inherit from `FunctionBase`
- Use `@bot_function("name")` decorator
- Implement `async def execute(self, **kwargs)` method
- Return `self.format_success_response()` or `self.format_error_response()`
- Include `intent_examples` for AI training
- Have proper type hints and docstrings

See `backend/functions/example.py` for a complete template.

## 🔒 Security Considerations

- **Environment Variables**: Never commit `.env` files
- **API Key Management**: Use environment-specific keys
- **Input Validation**: All function parameters are validated
- **Error Handling**: Errors don't expose sensitive information
- **Rate Limiting**: Built-in protection against spam

### Debug Commands

**Enable verbose logging**:
```bash
echo "LOG_LEVEL=DEBUG" >> .env
./start.sh restart
./start.sh logs -f
```

**Test backend directly**:
```bash
# Process message
curl -X POST http://localhost:8000/process-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "what is the weather in London?",
    "user_id": "test_user",
    "chat_id": "test_chat",
    "timestamp": "2025-11-01T12:00:00Z",
    "user_context": {
      "name": "Test User"
    }
  }'

# Execute function directly
curl -X POST http://localhost:8000/execute-function \
  -H "Content-Type: application/json" \
  -d '{
    "function_name": "weather",
    "parameters": {"location": "London"}
  }'

# List functions
curl http://localhost:8000/functions | jq

# Health check
curl http://localhost:8000/health
```

**Check logs**:
```bash
# All logs
./start.sh logs

# Follow logs in real-time
./start.sh logs -f

# Specific component
tail -f logs/whatsapp-bot.log
tail -f backend/logs/app.log
```

**Process management**:
```bash
# Check running processes
./start.sh status

# See what's using port 8000
lsof -i :8000

# Kill stuck processes
pkill -f "python.*main.py"
pkill -f "node.*index.js"
```

## 🎯 Roadmap

### Planned Features
- [ ] **Voice Message Support**: Speech-to-text with Whisper API
- [ ] **Image Analysis**: Vision API integration for image understanding
- [ ] **Multi-Language Support**: i18n for responses and commands
- [ ] **Plugin Marketplace**: Community-contributed functions
- [ ] **Web Dashboard**: Management interface with analytics
- [ ] **Docker Compose**: Full containerized deployment
- [ ] **Database Integration**: PostgreSQL for conversation history
- [ ] **Webhook Support**: Outbound notifications and integrations
- [ ] **Rate Limiting**: Per-user rate limits and quotas
- [ ] **Scheduling**: Cron-based scheduled messages
- [ ] **Group Management**: Advanced group chat features

### Recently Completed
- [x] **Code Refactoring**: Full PEP 8 compliance and English-only codebase
- [x] **Type Hints**: Complete type annotations across Python backend
- [x] **JSDoc Documentation**: Comprehensive documentation for JavaScript frontend
- [x] **Conversation Memory**: Redis and in-memory storage options
- [x] **Multi-Camera Support**: Concurrent camera capture
- [x] **Google Calendar Integration**: OAuth-based calendar management
- [x] **Access Control**: User whitelist for bot access


## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines:

1. **Code Quality**: Follow PEP 8 for Python and JSDoc for JavaScript
2. **Testing**: Include tests for new features
3. **Documentation**: Update README.md and add docstrings
4. **Examples**: Add intent_examples for AI training
5. **Commits**: Use clear, descriptive commit messages

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed development guidelines.

## 🙏 Acknowledgments

- [whatsapp-web.js](https://github.com/pedroslopez/whatsapp-web.js) - WhatsApp Web API
- [LangChain](https://github.com/langchain-ai/langchain) - LLM framework
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [OpenAI](https://openai.com/) - GPT API

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/nahuell1/whatsapp-bot-pylangchain/issues)
- **Discussions**: [GitHub Discussions](https://github.com/nahuell1/whatsapp-bot-pylangchain/discussions)
- **Documentation**: [Wiki](https://github.com/nahuell1/whatsapp-bot-pylangchain/wiki)

---

## 🤖 Example Conversation

```
User: "Hey bot, what's the weather like in Buenos Aires today?"

Bot: Weather for Buenos Aires

Current: 18°C
Partly cloudy

Forecast:
- 2025-11-02: 12°-22°
- 2025-11-03: 14°-24°, Rain 2.1mm
- 2025-11-04: 16°-26°

---

User: "can you show me all the cameras?"

Bot: Capture Multiple Cameras

Successful: 2
Failed: 0
Total: 2

Cameras captured:
- kitchen (HTTP)
- frontdoor (RTSP)

Completed: 01/11/2025 14:30:15

[Sends 2 camera images]

---

User: "turn on the office lights"

Bot: Office Lights has been turned on successfully!

---

User: "what's trending on Twitter?"

Bot: X/Twitter Trending Topics (Argentina)

Top trends:
1. #TrendingTopic
2. Technology
3. AI News
4. Buenos Aires
5. World Cup

Updated: 01/11/2025 14:35:00
```

---

**Built with ❤️ by [ndev](https://ndev.com.ar)**

**⭐ Star this repo if you find it useful!**
