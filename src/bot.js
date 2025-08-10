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
    // Track processed message IDs to avoid duplicates
    this.processedMessageIds = new Set();
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
        // Dedupe: skip if already processed
        if (messageInfo.message_id) {
            if (this.processedMessageIds.has(messageInfo.message_id)) {
                logger.debug(`Skipping duplicate message id=${messageInfo.message_id}`);
                return;
            }
            this.processedMessageIds.add(messageInfo.message_id);
            // Keep the set from growing unbounded
            if (this.processedMessageIds.size > 1000) {
                const first = this.processedMessageIds.values().next().value;
                this.processedMessageIds.delete(first);
            }
        }
        
        // Access control: only reply to allowed users if list configured
        if (config.ALLOWED_USER_IDS.length > 0 && !config.ALLOWED_USER_IDS.includes(messageInfo.user_id)) {
            logger.info(`Ignoring message from unauthorized user ${messageInfo.user_id}`);
            return; // silently ignore
        }
        
        logger.info(`Received message from ${messageInfo.user_id}: ${messageInfo.message.substring(0, 100)}...`);
        logger.debug('Message info:', messageInfo);

        // Ignore empty or whitespace-only messages
        if (!messageInfo.message || messageInfo.message.trim().length === 0) {
            logger.debug('Ignoring empty message');
            return;
        }

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
                    // Check if there are images to send
                    if (commandResult.image_data && commandResult.image_data.length > 0) {
                        logger.info(`Sending ${commandResult.image_data.length} image(s) from command`);
                        
                        // Send text response first
                        await message.reply(commandResult.message);
                        
                        // Send each image
                        for (const imageCapture of commandResult.image_data) {
                            if (imageCapture.image_data) {
                                await this.sendImageFromBase64(message, imageCapture.image_data);
                                logger.debug(`Sent image from camera: ${imageCapture.camera_name}`);
                            }
                        }
                        
                        logger.info(`Command with ${commandResult.image_data.length} image(s) executed successfully: ${commandResult.metadata?.command}`);
                    } else {
                        await message.reply(commandResult.message);
                        logger.info(`Command executed successfully: ${commandResult.metadata?.command}`);
                    }
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
                logger.debug('Found image in response.metadata.image_base64');
                await this.sendImageFromBase64(message, response.metadata.image_base64);
            }
            
            // Handle camera function responses with image_data
            if (response.result && response.result.image_data) {
                logger.debug('Found image in response.result.image_data');
                await this.sendImageFromBase64(message, response.result.image_data);
            }
            
            // Handle allcameras responses with successful captures - CHECK BOTH LOCATIONS
            let successfulCaptures = null;
            
            // First check metadata.result.successful_captures (for inference)
            if (response.metadata && response.metadata.result && response.metadata.result.successful_captures) {
                successfulCaptures = response.metadata.result.successful_captures;
                logger.debug(`Found ${successfulCaptures.length} successful captures in metadata.result`);
            }
            // Then check result.successful_captures (for direct commands)
            else if (response.result && response.result.successful_captures) {
                successfulCaptures = response.result.successful_captures;
                logger.debug(`Found ${successfulCaptures.length} successful captures in result`);
            }
            
            // Process the captures if found
            if (successfulCaptures) {
                for (const capture of successfulCaptures) {
                    if (capture.image_data) {
                        logger.debug(`Sending image for camera: ${capture.camera_name} (${capture.image_data.length} bytes)`);
                        await this.sendImageFromBase64(message, capture.image_data);
                        // Small delay between images to avoid rate limiting
                        await new Promise(resolve => setTimeout(resolve, 500));
                    } else {
                        logger.debug(`No image_data found for camera: ${capture.camera_name}`);
                    }
                }
            }
            
            // Debug response structure
            logger.debug('Response structure debug:', {
                hasMetadata: !!response.metadata,
                hasMetadataResult: !!(response.metadata && response.metadata.result),
                hasMetadataResultCaptures: !!(response.metadata && response.metadata.result && response.metadata.result.successful_captures),
                hasResult: !!response.result,
                hasResultCaptures: !!(response.result && response.result.successful_captures),
                metadataKeys: response.metadata ? Object.keys(response.metadata) : 'no metadata'
            });

        } catch (error) {
            logger.error('Error sending response:', error);
            await message.reply('🤖 I processed your request, but encountered an error sending the response.');
        }
    }

    async sendImageFromBase64(message, base64Image) {
        try {
            logger.debug('Attempting to send image from base64');
            const { MessageMedia } = require('whatsapp-web.js');
            
            // Create media from base64
            const media = new MessageMedia('image/jpeg', base64Image);
            logger.debug(`Created MessageMedia with ${base64Image.length} chars of base64 data`);
            
            // Send image
            await message.reply(media);
            logger.info('Image sent successfully');
            
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
