# Quick Start Guide

## Installation

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd whatsapp-bot-pylangchain
   ./setup.sh
   ```

2. **Configure environment**:
   ```bash
   # Edit .env file with your settings
   nano .env
   
   # At minimum, set your OpenAI API key:
   OPENAI_API_KEY=sk-your-api-key-here
   ```

3. **Start the bot**:
   ```bash
   ./start.sh
   ```

4. **Scan QR code** with WhatsApp mobile app when prompted

## Usage

### Available Commands

- `./start.sh start` - Start the bot
- `./start.sh stop` - Stop the bot
- `./start.sh restart` - Restart the bot
- `./start.sh status` - Check bot status
- `./start.sh logs` - View recent logs

### Bot Functions

The bot comes with several pre-built functions:

1. **Weather**: Get weather information
   - "What's the weather like in London?"
   - "Show me the forecast for New York"

2. **Home Assistant**: Control smart home devices
   - "Turn on the living room lights"
   - "What's the temperature in the bedroom?"

3. **IP Camera**: Get camera snapshots
   - "Show me the front door camera"
   - "Take a snapshot from the security camera"

4. **System Info**: Get system information
   - "Show me system status"
   - "What's the CPU usage?"

5. **Example**: Template function for development
   - "Run example function with message hello"

## Adding New Functions

1. Create a new file in `backend/functions/`:
   ```python
   # backend/functions/my_function.py
   from .base import FunctionBase
   
   class MyFunction(FunctionBase):
       def __init__(self):
           super().__init__(
               name="my_function",
               description="What your function does",
               parameters={
                   "param1": {
                       "type": "string",
                       "description": "Parameter description",
                       "required": True
                   }
               }
           )
       
       async def execute(self, **kwargs):
           # Your function logic here
           return self.format_success_response(
               {"result": "data"}, 
               "Function executed successfully"
           )
   ```

2. Restart the bot:
   ```bash
   ./start.sh restart
   ```

The function will be automatically loaded and available for use!

## Configuration

### Environment Variables

Key settings in `.env`:

```env
# Required
OPENAI_API_KEY=sk-your-api-key-here

# Optional
OPENAI_MODEL=gpt-4.1-nano-2025-04-14
BACKEND_HOST=localhost
BACKEND_PORT=8000
LOG_LEVEL=INFO

# Function-specific
HOME_ASSISTANT_URL=http://your-homeassistant:8123
HOME_ASSISTANT_TOKEN=your-token
IP_CAMERA_URL=http://your-camera/snapshot.jpg
```

### Function Configuration

Each function can have its own configuration variables. Add them to `.env` and use them in your function code.

## Troubleshooting

### Common Issues

1. **QR Code not showing**: Check that the frontend started successfully
2. **Backend not responding**: Check logs and ensure OpenAI API key is set
3. **Functions not working**: Check function syntax and restart the bot

### Debug Mode

Enable debug logging:
```bash
echo "LOG_LEVEL=DEBUG" >> .env
./start.sh restart
```

### View Logs

```bash
# All logs
./start.sh logs

# Live logs
tail -f logs/whatsapp-bot.log

# Error logs only
tail -f logs/error.log
```

## Development

See `docs/DEVELOPMENT.md` for detailed development information.

## Security

- Never commit your `.env` file
- Use environment-specific API keys
- Regularly update dependencies
- Monitor logs for suspicious activity

## Support

- Check the logs for error messages
- Consult the development documentation
- Review function examples for implementation guidance

---

**Happy Bot Building! 🤖**
