/**
 * WhatsApp Bot Main Class
 * 
 * Handles message processing, command execution, and communication with Python backend.
 * Manages message deduplication, access control, and media handling.
 * 
 * @module bot
 */

const axios = require('axios');
const { MessageMedia } = require('whatsapp-web.js');
const logger = require('./utils/logger');
const MessageProcessor = require('./message-processor');
const CommandHandler = require('./command-handler');
const config = require('./config');

// Constants
const MAX_PROCESSED_MESSAGE_IDS = 1000;
const IMAGE_SEND_DELAY_MS = 500;
const MESSAGE_CHUNK_DELAY_MS = 500;

/**
 * WhatsApp Bot class for handling messages and backend communication
 */
class WhatsAppBot {
    /**
     * Initialize WhatsApp bot
     * @param {Client} client - WhatsApp client instance
     */
    constructor(client) {
        this.client = client;
        this.messageProcessor = new MessageProcessor();
        this.commandHandler = new CommandHandler();
        this.processedMessageIds = new Set();
        this.setupEventHandlers();
        logger.info('✅ WhatsApp Bot initialized successfully');
        logger.info(`📋 Registered event handlers: ${this.client.eventNames ? this.client.eventNames().join(', ') : 'N/A'}`);
    }

    /**
     * Set up event handlers for WhatsApp client
     * Registers handlers for message, message_create, reactions, and group events
     */
    setupEventHandlers() {
        const messageHandler = async (message) => {
            try {
                const from = (message && message.from) || 'unknown';
                const type = (message && message.type) || 'unknown';
                const body = (message && message.body) || '';
                logger.info(`📨 Message received from=${from} type=${type} body="${body.substring(0, 50)}"`);
                
                await this.handleMessage(message);
            } catch (error) {
                logger.error('Error handling message:', error);
                try {
                    await message.reply('Sorry, I encountered an error processing your message. Please try again.');
                } catch (replyError) {
                    logger.error('Error sending error reply:', replyError);
                }
            }
        };
        
        this.client.on('message', messageHandler);
        this.client.on('message_create', messageHandler);
        
        logger.info('Message handlers registered for both "message" and "message_create" events');

        this.client.on('message_reaction', async (reaction) => {
            logger.debug('Message reaction received:', reaction);
        });

        this.client.on('group_join', async (notification) => {
            logger.debug('Group join notification:', notification);
        });

        this.client.on('group_leave', async (notification) => {
            logger.debug('Group leave notification:', notification);
        });
    }

    /**
     * Handle incoming WhatsApp message
     * @param {Message} message - WhatsApp message object
     */
    async handleMessage(message) {
        const startTime = Date.now();
        
        if (message.fromMe) {
            return;
        }

        if (message.from.includes('status@broadcast')) {
            return;
        }

        const messageInfo = await this.messageProcessor.extractMessageInfo(message);
        
        if (messageInfo.message_id) {
            if (this.processedMessageIds.has(messageInfo.message_id)) {
                logger.debug(`Skipping duplicate message id=${messageInfo.message_id}`);
                return;
            }
            this.processedMessageIds.add(messageInfo.message_id);
            
            if (this.processedMessageIds.size > MAX_PROCESSED_MESSAGE_IDS) {
                const first = this.processedMessageIds.values().next().value;
                this.processedMessageIds.delete(first);
            }
        }
        
        if (config.ALLOWED_USER_IDS.length > 0 && !config.ALLOWED_USER_IDS.includes(messageInfo.user_id)) {
            logger.info(`Ignoring message from unauthorized user ${messageInfo.user_id}`);
            return;
        }
        
        logger.info(`Received message from ${messageInfo.user_id}: ${messageInfo.message.substring(0, 100)}...`);
        logger.debug('Message info:', messageInfo);

        if (!messageInfo.message || messageInfo.message.trim().length === 0) {
            logger.debug('Ignoring empty message');
            return;
        }

        if (messageInfo.message.length > config.MAX_MESSAGE_LENGTH) {
            await message.reply(`⚠️ Your message is too long (${messageInfo.message.length} characters). Please keep messages under ${config.MAX_MESSAGE_LENGTH} characters.`);
            return;
        }

        const chat = await message.getChat();
        if (!config.ENABLE_GROUP_MESSAGES && chat.isGroup) {
            logger.info(`Ignoring group message in '${chat.name}' (ENABLE_GROUP_MESSAGES=false)`);
            return;
        }
        if (config.ENABLE_TYPING_INDICATOR) {
            await chat.sendStateTyping();
        }

        try {
            if (this.commandHandler.isCommand(messageInfo.message)) {
                logger.info('Processing direct command:', messageInfo.message);
                
                if (messageInfo.message.toLowerCase().startsWith('!help')) {
                    const helpArgs = messageInfo.message.substring(5).trim().split(/\s+/).filter(arg => arg.length > 0);
                    const helpResponse = await this.commandHandler.handleHelpCommand(helpArgs);
                    await message.reply(helpResponse);
                    
                    const processingTime = Date.now() - startTime;
                    logger.info(`Help command processed in ${processingTime}ms`);
                    return;
                }
                
                const commandResult = await this.commandHandler.executeCommand(messageInfo.message, messageInfo.user_context);
                
                if (commandResult.success) {
                    if (commandResult.image_data && commandResult.image_data.length > 0) {
                        logger.info(`Sending ${commandResult.image_data.length} image(s) from command`);
                        
                        await message.reply(commandResult.message);
                        
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
            
            const response = await this.sendToBackend(messageInfo);
            await this.sendResponse(message, response);
            
            const processingTime = Date.now() - startTime;
            logger.info(`Message processed in ${processingTime}ms`);
            
        } catch (error) {
            logger.error('Error processing message with backend:', error);
            await message.reply('🤖 Sorry, I\'m having trouble processing your message right now. Please try again in a moment.');
        } finally {
            if (config.ENABLE_TYPING_INDICATOR) {
                await chat.clearState();
            }
        }
    }

    /**
     * Send message to Python backend for processing
     * @param {Object} messageInfo - Message information object
     * @returns {Promise<Object>} Backend response
     */
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
                logger.error(`Backend error ${error.response.status}: ${JSON.stringify(error.response.data)}`);
                throw new Error(`Backend error: ${error.response.data.detail || error.response.data.message || 'Unknown error'}`);
            } else if (error.request) {
                logger.error('No response from backend:', error.message);
                throw new Error('Backend is not responding. Please try again later.');
            } else {
                logger.error('Error setting up backend request:', error.message);
                throw new Error('Failed to communicate with backend.');
            }
        }
    }

    /**
     * Send response to user with text and media handling
     * @param {Message} message - Original WhatsApp message
     * @param {Object} response - Backend response object
     */
    async sendResponse(message, response) {
        try {
            let responseMessage = response.message;
            
            if (response.intent === 'function_call' && response.function_name) {
                responseMessage = `🔧 *${response.function_name}*\n\n${responseMessage}`;
            }

            if (responseMessage.length > config.MAX_MESSAGE_LENGTH) {
                const chunks = this.splitMessage(responseMessage, config.MAX_MESSAGE_LENGTH);
                for (const chunk of chunks) {
                    await message.reply(chunk);
                    await this.delay(MESSAGE_CHUNK_DELAY_MS);
                }
            } else {
                await message.reply(responseMessage);
            }

            if (response.metadata && response.metadata.image_base64) {
                logger.debug('Found image in response.metadata.image_base64');
                await this.sendImageFromBase64(message, response.metadata.image_base64);
            }
            
            if (response.result && response.result.image_data) {
                logger.debug('Found image in response.result.image_data');
                await this.sendImageFromBase64(message, response.result.image_data);
            }
            
            let successfulCaptures = null;
            
            if (response.metadata && response.metadata.result && response.metadata.result.successful_captures) {
                successfulCaptures = response.metadata.result.successful_captures;
                logger.debug(`Found ${successfulCaptures.length} successful captures in metadata.result`);
            } else if (response.result && response.result.successful_captures) {
                successfulCaptures = response.result.successful_captures;
                logger.debug(`Found ${successfulCaptures.length} successful captures in result`);
            }
            
            if (successfulCaptures) {
                for (const capture of successfulCaptures) {
                    if (capture.image_data) {
                        logger.debug(`Sending image for camera: ${capture.camera_name} (${capture.image_data.length} bytes)`);
                        await this.sendImageFromBase64(message, capture.image_data);
                        await this.delay(IMAGE_SEND_DELAY_MS);
                    } else {
                        logger.debug(`No image_data found for camera: ${capture.camera_name}`);
                    }
                }
            }
            
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

    /**
     * Send image to user from base64 data
     * @param {Message} message - Original WhatsApp message
     * @param {string} base64Image - Base64 encoded image data
     */
    async sendImageFromBase64(message, base64Image) {
        try {
            logger.debug('Attempting to send image from base64');
            
            const media = new MessageMedia('image/jpeg', base64Image);
            logger.debug(`Created MessageMedia with ${base64Image.length} chars of base64 data`);
            
            await message.reply(media);
            logger.info('Image sent successfully');
            
        } catch (error) {
            logger.error('Error sending image:', error);
            await message.reply('📸 I captured the image but couldn\'t send it. Please try again.');
        }
    }

    /**
     * Split long message into chunks
     * @param {string} message - Message to split
     * @param {number} maxLength - Maximum chunk length
     * @returns {Array<string>} Message chunks
     */
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

    /**
     * Delay execution
     * @param {number} ms - Milliseconds to delay
     * @returns {Promise<void>}
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Check backend health status
     * @returns {Promise<Object>} Health status object
     */
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

    /**
     * Get list of available backend functions
     * @returns {Promise<Object>} Functions list object
     */
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
