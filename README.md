# WhatsApp Bot with AI Intent Detection & Dynamic Functions

A professional WhatsApp bot system with intelligent message processing, featuring **dynamic intent detection**, **automatic function discovery**, and **multi-camera support**. Built with Node.js frontend (whatsapp-web.js) and Python backend using LangChain and GPT-4.

## 🚀 Key Features

### 🧠 Intelligent AI Processing
- **Dynamic Intent Detection**: Uses GPT-4 to automatically detect user intent and function calls
- **Smart Parameter Inference**: Automatically extracts and validates function parameters from natural language
- **Context-Aware Responses**: Maintains conversation context and provides intelligent replies

### 🔧 Automatic Function Discovery
- **Zero Configuration**: Drop Python functions into `/backend/functions/` and they're automatically available
- **Dynamic Examples**: Functions include training examples for better AI understanding
- **Hot Reloading**: Functions are loaded dynamically without restart (during development)

### 📸 Advanced Camera System
- **Multi-Protocol Support**: RTSP, HTTP, ONVIF, and MJPEG cameras
- **Automatic Discovery**: Environment-based camera configuration with auto-detection
- **Simultaneous Capture**: Capture from multiple cameras concurrently
- **Base64 Image Transmission**: Seamless image sharing through WhatsApp

### 🏠 Smart Home Integration
- **Home Assistant Support**: Full integration with Home Assistant automation
- **Entity Control**: Turn on/off lights, scenes, automations, and more
- **State Monitoring**: Check sensor states and device information

### 🌍 Rich Function Library
- **Weather Information**: Real-time weather and forecasts (OpenMeteo API)
- **News Updates**: Latest news from Reddit Argentina
- **System Monitoring**: CPU, memory, disk usage, and system information
- **Dollar Exchange**: Argentine peso/USD exchange rates

## 📋 Architecture

```mermaid
graph TB
    A[WhatsApp Message] --> B[Node.js Frontend]
    B --> C{Message Type}
    C -->|"!command"| D[Direct Command Handler]
    C -->|Natural Language| E[Python Backend]
    E --> F[GPT-4 Intent Detector]
    F --> G[Dynamic Function Manager]
    G --> H[Function Execution]
    D --> I[Function Execution]
    H --> J[Response Processing]
    I --> J
    J --> K[WhatsApp Response]
    K -->|Images| L[Base64 Media Handler]
    
    style F fill:#e1f5fe
    style G fill:#f3e5f5
    style H fill:#e8f5e8
```

## 🛠 Installation

### Prerequisites
- **Node.js** 18+ with npm
- **Python** 3.9+
- **OpenAI API Key** (GPT-4 access required)

### Quick Setup

1. **Clone and Setup**:
```bash
git clone https://github.com/nahuell1/whatsapp-bot-pylangchain.git
cd whatsapp-bot-pylangchain
chmod +x setup.sh start.sh
./setup.sh
```

2. **Configure Environment**:
```bash
cp .env.example .env
# Edit .env with your settings - AT MINIMUM set OPENAI_API_KEY
nano .env
```

3. **Start the Bot**:
```bash
./start.sh
```

4. **Scan QR Code** with WhatsApp mobile app when prompted

That's it! The bot is ready to use. 🎉

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
!weather Buenos Aires          # Weather information
!allcameras                    # All camera snapshots
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
# Required
OPENAI_API_KEY=sk-your-api-key-here

# Backend
BACKEND_HOST=localhost
BACKEND_PORT=8000
OPENAI_MODEL=gpt-4.1-nano-2025-04-14

# Logging  
LOG_LEVEL=INFO

# Timeouts
FUNCTION_TIMEOUT=30
MAX_MESSAGE_LENGTH=1000
```

### Camera Configuration
```bash
# Auto-discovery format: CAMERA_[NAME]_[CONFIG]
CAMERA_KITCHEN_IP=192.168.1.100
CAMERA_KITCHEN_TYPE=http
CAMERA_KITCHEN_PATH=/snapshot.jpg
CAMERA_KITCHEN_USERNAME=user
CAMERA_KITCHEN_PASSWORD=pass

# RTSP example
CAMERA_FRONTDOOR_IP=192.168.1.101  
CAMERA_FRONTDOOR_TYPE=rtsp
CAMERA_FRONTDOOR_URL=rtsp://user:pass@192.168.1.101/stream1
```

### Home Assistant Integration
```bash
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HOME_ASSISTANT_TOKEN=your_long_lived_access_token
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
- **GPT-4 Powered**: Uses advanced language model for intent classification
- **Dynamic Training**: Functions provide examples that automatically update AI prompts
- **Parameter Extraction**: Intelligent extraction of function parameters from natural language
- **Confidence Scoring**: Each detection includes confidence levels

### Function Management
- **Auto-Discovery**: Functions are automatically loaded from the `/functions` directory
- **Decorator-Based**: Simple `@bot_function()` decorator for registration  
- **Inheritance System**: Base class provides common functionality
- **Error Handling**: Comprehensive error handling and user-friendly messages

### Message Processing Pipeline
1. **Message Reception** (WhatsApp → Node.js)
2. **Command Detection** (Direct `!command` vs Natural Language)
3. **Intent Analysis** (GPT-4 classification)
4. **Function Execution** (Parameter validation & execution)
5. **Response Formatting** (Text + Media handling)
6. **Delivery** (WhatsApp response with images/text)

## 🧪 Development

### Project Structure
```
whatsapp-bot-pylangchain/
├── src/                      # Node.js Frontend
│   ├── bot.js               # Main WhatsApp bot logic
│   ├── command-handler.js   # Direct command processing
│   ├── message-processor.js # Message parsing utilities
│   └── utils/              # Utility modules
├── backend/                 # Python Backend
│   ├── main.py             # FastAPI application
│   ├── core/               # Core functionality
│   │   ├── intent_detector.py  # GPT-4 intent detection
│   │   ├── function_manager.py # Function loading/execution
│   │   ├── chat_handler.py    # Chat conversation handling
│   │   └── config.py         # Configuration management
│   ├── functions/          # Function modules (auto-loaded)
│   │   ├── base.py         # Base function class
│   │   ├── camera.py       # Camera functionality
│   │   ├── allcameras.py   # Multi-camera support
│   │   ├── weather.py      # Weather information
│   │   ├── home_assistant.py # Smart home integration
│   │   ├── dollar.py       # Exchange rates
│   │   ├── news.py         # News updates
│   │   └── system_info.py  # System monitoring
│   └── models/             # Data models
└── docs/                   # Documentation
```

### Running Tests
```bash
# Python backend tests
cd backend && python -m pytest tests/

# Node.js frontend tests  
npm test

# Integration tests
npm run test:integration
```

### Contributing
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-function`
3. Add your function in `/backend/functions/`
4. Include examples in your function for AI training
5. Test with both natural language and direct commands
6. Submit a pull request

## 🔒 Security Considerations

- **Environment Variables**: Never commit `.env` files
- **API Key Management**: Use environment-specific keys
- **Input Validation**: All function parameters are validated
- **Error Handling**: Errors don't expose sensitive information
- **Rate Limiting**: Built-in protection against spam

## 🐛 Troubleshooting

### Common Issues

**QR Code not showing**:
```bash
./start.sh logs                # Check frontend logs
# Ensure WhatsApp web session isn't active elsewhere
```

**Backend not responding**:
```bash
curl http://localhost:8000/health  # Test backend
# Check OPENAI_API_KEY is set correctly
```

**Functions not detected**:
```bash
curl http://localhost:8000/functions  # List available functions
./start.sh restart                    # Reload functions
```

**Camera issues**:
```bash
# Check camera configurations in .env
# Test camera URLs directly in browser
# Verify network connectivity
```

### Debug Information
```bash
# Enable debug mode
echo "LOG_LEVEL=DEBUG" >> .env
./start.sh restart

# Monitor logs
./start.sh logs -f

# Test specific function
curl -X POST http://localhost:8000/execute-function \\
  -H "Content-Type: application/json" \\
  -d '{"function_name": "weather", "parameters": {"location": "Madrid"}}'
```

## 🎯 Roadmap

- [ ] **Voice Message Support**: Process audio messages with speech-to-text
- [ ] **Database Integration**: Persistent conversation history
- [ ] **Multi-Language Support**: Internationalization
- [ ] **Plugin Marketplace**: Community-contributed functions  
- [ ] **Web Dashboard**: Management interface
- [ ] **Docker Deployment**: Containerized deployment options

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🤖 Example Conversation

```
User: "Hey bot, what's the weather like in Buenos Aires today?"

Bot: 🔧 weather

🌍 Weather for Buenos Aires

🌡️ Current: 18°C
☁️ Partly cloudy

📅 Forecast:
• 2025-07-19: 12°-22°
• 2025-07-20: 14°-24°, 🌧️ 2.1mm  
• 2025-07-21: 16°-26°

---

User: "can you show me all the cameras?"

Bot: 🔧 allcameras

📸 Capture Multiple Cameras

✅ Successful: 2
❌ Failed: 0  
📱 Total: 2

**Cameras captured:**
• kitchen (HTTP)
• window (RTSP)

🕐 Completed: 19/07/2025 14:30:15

[Sends 2 camera images]

---

User: "turn on the office scene"

Bot: 🔧 home_assistant

🏠 Office On has been turned on successfully!
```

**Built with ❤️ community**
