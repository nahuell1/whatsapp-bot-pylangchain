/**
 * WhatsApp Bot Main Class
 * Handles message processing and communication with Python backend
 */

const axios = require('axios');
const logger = require('./utils/logger');
const MessageProcessor = require('./message-processor');
const CommandHandler = require('./command-handler');
const config = require('./config');

class WhatsAppBot {
    constructor(client) {
        this.client = client;
        this.messageProcessor = new MessageProcessor();
        this.commandHandler = new CommandHandler();
        this.setupEventHandlers();
        logger.info('WhatsApp Bot initialized');
    }

    setupEventHandlers() {
        // Handle incoming messages
        this.client.on('message', async (message) => {
            try {
                await this.handleMessage(message);
            } catch (error) {
                logger.error('Error handling message:', error);
                // Send error message to user
                await message.reply('Sorry, I encountered an error processing your message. Please try again.');
            }
        });

        // Handle message reactions (optional)
        this.client.on('message_reaction', async (reaction) => {
            logger.debug('Message reaction received:', reaction);
        });

        // Handle group join/leave events (optional)
        this.client.on('group_join', async (notification) => {
            logger.debug('Group join notification:', notification);
        });

        this.client.on('group_leave', async (notification) => {
            logger.debug('Group leave notification:', notification);
        });
    }

    async handleMessage(message) {
        const startTime = Date.now();
        
        // Skip messages from the bot itself
        if (message.fromMe) {
            return;
        }

        // Skip status messages
        if (message.from.includes('status@broadcast')) {
            return;
        }

        // Get message info
        const messageInfo = await this.messageProcessor.extractMessageInfo(message);
        
        logger.info(`Received message from ${messageInfo.user_id}: ${messageInfo.message.substring(0, 100)}...`);
        logger.debug('Message info:', messageInfo);

        // Check message length
        if (messageInfo.message.length > config.MAX_MESSAGE_LENGTH) {
            await message.reply(`⚠️ Your message is too long (${messageInfo.message.length} characters). Please keep messages under ${config.MAX_MESSAGE_LENGTH} characters.`);
            return;
        }

        // Show typing indicator
        const chat = await message.getChat();
        if (config.ENABLE_TYPING_INDICATOR) {
            await chat.sendStateTyping();
        }

        try {
            // Check if message is a direct command
            if (this.commandHandler.isCommand(messageInfo.message)) {
                logger.info('Processing direct command:', messageInfo.message);
                
                // Handle special help command
                if (messageInfo.message.toLowerCase().startsWith('!help')) {
                    const helpArgs = messageInfo.message.substring(5).trim().split(/\s+/).filter(arg => arg.length > 0);
                    const helpResponse = await this.commandHandler.handleHelpCommand(helpArgs);
                    await message.reply(helpResponse);
                    
                    const processingTime = Date.now() - startTime;
                    logger.info(`Help command processed in ${processingTime}ms`);
                    return;
                }
                
                // Execute direct command
                const commandResult = await this.commandHandler.executeCommand(messageInfo.message, messageInfo.user_context);
                
                if (commandResult.success) {
                    await message.reply(commandResult.message);
                    logger.info(`Command executed successfully: ${commandResult.metadata?.command}`);
                } else {
                    await message.reply(commandResult.message);
                    logger.warn(`Command execution failed: ${commandResult.message}`);
                }
                
                const processingTime = Date.now() - startTime;
                logger.info(`Command processed in ${processingTime}ms`);
                return;
            }
            
            // Process message with backend (AI inference)
            const response = await this.sendToBackend(messageInfo);
            
            // Send response
            await this.sendResponse(message, response);
            
            const processingTime = Date.now() - startTime;
            logger.info(`Message processed in ${processingTime}ms`);
            
        } catch (error) {
            logger.error('Error processing message with backend:', error);
            await message.reply('🤖 Sorry, I\'m having trouble processing your message right now. Please try again in a moment.');
        } finally {
            // Clear typing indicator
            if (config.ENABLE_TYPING_INDICATOR) {
                await chat.clearState();
            }
        }
    }

    async sendToBackend(messageInfo) {
        try {
            logger.debug('Sending to backend:', messageInfo);
            
            const response = await axios.post(`${config.BACKEND_URL}/process-message`, messageInfo, {
                timeout: config.BACKEND_TIMEOUT || 30000,
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            logger.debug('Backend response:', response.data);
            return response.data;
        } catch (error) {
            if (error.response) {
                // Backend returned an error response
                logger.error(`Backend error ${error.response.status}: ${JSON.stringify(error.response.data)}`);
                throw new Error(`Backend error: ${error.response.data.detail || error.response.data.message || 'Unknown error'}`);
            } else if (error.request) {
                // Request was made but no response received
                logger.error('No response from backend:', error.message);
                throw new Error('Backend is not responding. Please try again later.');
            } else {
                // Something else happened
                logger.error('Error setting up backend request:', error.message);
                throw new Error('Failed to communicate with backend.');
            }
        }
    }

    async sendResponse(message, response) {
        try {
            let responseMessage = response.message;
            
            // Add function execution indicator
            if (response.intent === 'function_call' && response.function_name) {
                responseMessage = `🔧 *${response.function_name}*\n\n${responseMessage}`;
            }

            // Handle long messages by splitting them
            if (responseMessage.length > config.MAX_MESSAGE_LENGTH) {
                const chunks = this.splitMessage(responseMessage, config.MAX_MESSAGE_LENGTH);
                for (const chunk of chunks) {
                    await message.reply(chunk);
                    // Small delay between chunks to avoid rate limiting
                    await this.delay(500);
                }
            } else {
                await message.reply(responseMessage);
            }

            // Handle media responses (e.g., camera images)
            if (response.metadata && response.metadata.image_base64) {
                await this.sendImageFromBase64(message, response.metadata.image_base64);
            }

        } catch (error) {
            logger.error('Error sending response:', error);
            await message.reply('🤖 I processed your request, but encountered an error sending the response.');
        }
    }

    async sendImageFromBase64(message, base64Image) {
        try {
            const { MessageMedia } = require('whatsapp-web.js');
            
            // Create media from base64
            const media = new MessageMedia('image/jpeg', base64Image);
            
            // Send image
            await message.reply(media);
            
        } catch (error) {
            logger.error('Error sending image:', error);
            await message.reply('📸 I captured the image but couldn\'t send it. Please try again.');
        }
    }

    splitMessage(message, maxLength) {
        const chunks = [];
        let currentChunk = '';
        const lines = message.split('\\n');

        for (const line of lines) {
            if (currentChunk.length + line.length + 1 <= maxLength) {
                currentChunk += (currentChunk ? '\\n' : '') + line;
            } else {
                if (currentChunk) {
                    chunks.push(currentChunk);
                }
                
                // If a single line is too long, split it
                if (line.length > maxLength) {
                    const words = line.split(' ');
                    currentChunk = '';
                    
                    for (const word of words) {
                        if (currentChunk.length + word.length + 1 <= maxLength) {
                            currentChunk += (currentChunk ? ' ' : '') + word;
                        } else {
                            if (currentChunk) {
                                chunks.push(currentChunk);
                            }
                            currentChunk = word;
                        }
                    }
                } else {
                    currentChunk = line;
                }
            }
        }

        if (currentChunk) {
            chunks.push(currentChunk);
        }

        return chunks;
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async getBackendHealth() {
        try {
            const response = await axios.get(`${config.BACKEND_URL}/health`, {
                timeout: 5000
            });
            return response.data;
        } catch (error) {
            logger.error('Backend health check failed:', error.message);
            return { status: 'unhealthy', error: error.message };
        }
    }

    async getAvailableFunctions() {
        try {
            const response = await axios.get(`${config.BACKEND_URL}/functions`, {
                timeout: 5000
            });
            return response.data;
        } catch (error) {
            logger.error('Failed to get available functions:', error.message);
            return { functions: [] };
        }
    }
}

module.exports = WhatsAppBot;
