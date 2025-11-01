/**
 * Message Processor Module
 * 
 * Handles extraction and preprocessing of WhatsApp messages.
 * Supports text, image, audio, video, document, location, contact, and sticker messages.
 * 
 * @module message-processor
 */

const logger = require('./utils/logger');

// Message type constants
const MESSAGE_TYPES = {
    TEXT: 'text',
    IMAGE: 'image',
    AUDIO: 'audio',
    VIDEO: 'video',
    DOCUMENT: 'document',
    LOCATION: 'location',
    CONTACT: 'vcard',
    STICKER: 'sticker'
};

/**
 * Message processor class for extracting and formatting message information
 */
class MessageProcessor {
    constructor() {
        this.messageTypes = MESSAGE_TYPES;
    }

    /**
     * Extract message information from WhatsApp message
     * @param {Message} message - WhatsApp message object
     * @returns {Promise<Object>} Extracted message information
     */
    async extractMessageInfo(message) {
        try {
            const contact = await message.getContact();
            const chat = await message.getChat();
            
            logger.debug('Contact info:', {
                id: contact.id,
                name: contact.name,
                pushname: contact.pushname
            });
            
            logger.debug('Chat info:', {
                id: chat.id,
                isGroup: chat.isGroup,
                name: chat.name
            });
            
            const messageInfo = {
                message: message.body || '',
                user_id: contact.id.user,
                chat_id: chat.id._serialized,
                message_id: message.id ? message.id._serialized : undefined,
                timestamp: new Date(message.timestamp * 1000).toISOString(),
                message_type: this.getMessageType(message)
            };
            
            logger.debug('Initial messageInfo:', messageInfo);

            switch (messageInfo.message_type) {
                case this.messageTypes.TEXT:
                    break;
                
                case this.messageTypes.IMAGE:
                    messageInfo.message = await this.handleImageMessage(message);
                    break;
                
                case this.messageTypes.AUDIO:
                    messageInfo.message = await this.handleAudioMessage(message);
                    break;
                
                case this.messageTypes.VIDEO:
                    messageInfo.message = await this.handleVideoMessage(message);
                    break;
                
                case this.messageTypes.DOCUMENT:
                    messageInfo.message = await this.handleDocumentMessage(message);
                    break;
                
                case this.messageTypes.LOCATION:
                    messageInfo.message = await this.handleLocationMessage(message);
                    break;
                
                case this.messageTypes.CONTACT:
                    messageInfo.message = await this.handleContactMessage(message);
                    break;
                
                case this.messageTypes.STICKER:
                    messageInfo.message = await this.handleStickerMessage(message);
                    break;
                
                default:
                    messageInfo.message = message.body || 'Unsupported message type';
            }

            messageInfo.user_context = {
                name: contact.name || contact.pushname || 'Unknown',
                phone: contact.number,
                is_business: contact.isBusiness,
                is_group: chat.isGroup,
                group_name: chat.isGroup ? chat.name : null
            };

            return messageInfo;

        } catch (error) {
            logger.error('Error extracting message info:', error);
            
            return {
                message: message.body || 'Error processing message',
                user_id: 'unknown',
                chat_id: 'unknown',
                timestamp: new Date().toISOString(),
                message_type: 'text',
                user_context: {
                    name: 'Unknown',
                    phone: 'unknown',
                    is_business: false,
                    is_group: false,
                    group_name: null
                }
            };
        }
    }

    /**
     * Determine message type from WhatsApp message
     * @param {Message} message - WhatsApp message object
     * @returns {string} Message type
     */
    getMessageType(message) {
        if (message.hasMedia) {
            return message.type;
        } else if (message.type === 'location') {
            return this.messageTypes.LOCATION;
        } else if (message.type === 'vcard') {
            return this.messageTypes.CONTACT;
        } else {
            return this.messageTypes.TEXT;
        }
    }

    /**
     * Handle image message
     * @param {Message} message - WhatsApp message with image
     * @returns {Promise<string>} Image description
     */
    async handleImageMessage(message) {
        try {
            await message.downloadMedia();
            const caption = message.body || '';
            return `[Image received${caption ? `: ${caption}` : ''}] - Image processing not implemented yet`;
        } catch (error) {
            logger.error('Error handling image message:', error);
            return '[Image received but could not be processed]';
        }
    }

    /**
     * Handle audio message
     * @param {Message} message - WhatsApp message with audio
     * @returns {Promise<string>} Audio description
     */
    async handleAudioMessage(message) {
        try {
            return '[Audio message received] - Audio processing not implemented yet';
        } catch (error) {
            logger.error('Error handling audio message:', error);
            return '[Audio message received but could not be processed]';
        }
    }

    /**
     * Handle video message
     * @param {Message} message - WhatsApp message with video
     * @returns {Promise<string>} Video description
     */
    async handleVideoMessage(message) {
        try {
            const caption = message.body || '';
            return `[Video received${caption ? `: ${caption}` : ''}] - Video processing not implemented yet`;
        } catch (error) {
            logger.error('Error handling video message:', error);
            return '[Video received but could not be processed]';
        }
    }

    /**
     * Handle document message
     * @param {Message} message - WhatsApp message with document
     * @returns {Promise<string>} Document description
     */
    async handleDocumentMessage(message) {
        try {
            const media = await message.downloadMedia();
            const filename = media.filename || 'document';
            return `[Document received: ${filename}] - Document processing not implemented yet`;
        } catch (error) {
            logger.error('Error handling document message:', error);
            return '[Document received but could not be processed]';
        }
    }

    /**
     * Handle location message
     * @param {Message} message - WhatsApp message with location
     * @returns {Promise<string>} Location description
     */
    async handleLocationMessage(message) {
        try {
            const location = message.location;
            return `[Location shared: ${location.latitude}, ${location.longitude}] - Location: ${location.description || 'No description'}`;
        } catch (error) {
            logger.error('Error handling location message:', error);
            return '[Location shared but could not be processed]';
        }
    }

    /**
     * Handle contact message
     * @param {Message} message - WhatsApp message with contact
     * @returns {Promise<string>} Contact description
     */
    async handleContactMessage(message) {
        try {
            const contact = message.vCards[0];
            const name = contact.split('\\n').find(line => line.startsWith('FN:'))?.substring(3) || 'Unknown';
            return `[Contact shared: ${name}] - Contact processing not implemented yet`;
        } catch (error) {
            logger.error('Error handling contact message:', error);
            return '[Contact shared but could not be processed]';
        }
    }

    /**
     * Handle sticker message
     * @param {Message} message - WhatsApp message with sticker
     * @returns {Promise<string>} Sticker description
     */
    async handleStickerMessage(message) {
        try {
            return '[Sticker received] - Sticker processing not implemented yet';
        } catch (error) {
            logger.error('Error handling sticker message:', error);
            return '[Sticker received but could not be processed]';
        }
    }

    /**
     * Preprocess and clean message text
     * @param {string} message - Raw message text
     * @returns {string} Cleaned message
     */
    preprocessMessage(message) {
        let cleanMessage = message.trim();
        cleanMessage = cleanMessage.replace(/\\s+/g, ' ');
        cleanMessage = cleanMessage.replace(/\\*([^*]+)\\*/g, '$1');
        cleanMessage = cleanMessage.replace(/_([^_]+)_/g, '$1');
        cleanMessage = cleanMessage.replace(/~([^~]+)~/g, '$1');
        return cleanMessage;
    }
}

module.exports = MessageProcessor;
