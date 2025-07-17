/**
 * Message Processor
 * Handles message extraction and preprocessing
 */

const logger = require('./utils/logger');

class MessageProcessor {
    constructor() {
        this.messageTypes = {
            TEXT: 'text',
            IMAGE: 'image',
            AUDIO: 'audio',
            VIDEO: 'video',
            DOCUMENT: 'document',
            LOCATION: 'location',
            CONTACT: 'vcard',
            STICKER: 'sticker'
        };
    }

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
            
            // Extract basic message info
            const messageInfo = {
                message: message.body || '',
                user_id: contact.id.user,
                chat_id: chat.id._serialized,
                timestamp: new Date(message.timestamp * 1000).toISOString(),
                message_type: this.getMessageType(message)
            };
            
            logger.debug('Initial messageInfo:', messageInfo);

            // Handle different message types
            switch (messageInfo.message_type) {
                case this.messageTypes.TEXT:
                    // Text message is already in message.body
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

            // Add user context
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
            
            // Return basic fallback info
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

    async handleImageMessage(message) {
        try {
            const media = await message.downloadMedia();
            
            // For now, just return a description
            // In the future, we could integrate with image recognition
            const caption = message.body || '';
            return `[Image received${caption ? `: ${caption}` : ''}] - Image processing not implemented yet`;
            
        } catch (error) {
            logger.error('Error handling image message:', error);
            return '[Image received but could not be processed]';
        }
    }

    async handleAudioMessage(message) {
        try {
            // For now, just return a description
            // In the future, we could integrate with speech-to-text
            return '[Audio message received] - Audio processing not implemented yet';
            
        } catch (error) {
            logger.error('Error handling audio message:', error);
            return '[Audio message received but could not be processed]';
        }
    }

    async handleVideoMessage(message) {
        try {
            const caption = message.body || '';
            return `[Video received${caption ? `: ${caption}` : ''}] - Video processing not implemented yet`;
            
        } catch (error) {
            logger.error('Error handling video message:', error);
            return '[Video received but could not be processed]';
        }
    }

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

    async handleLocationMessage(message) {
        try {
            const location = message.location;
            return `[Location shared: ${location.latitude}, ${location.longitude}] - Location: ${location.description || 'No description'}`;
            
        } catch (error) {
            logger.error('Error handling location message:', error);
            return '[Location shared but could not be processed]';
        }
    }

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

    async handleStickerMessage(message) {
        try {
            return '[Sticker received] - Sticker processing not implemented yet';
            
        } catch (error) {
            logger.error('Error handling sticker message:', error);
            return '[Sticker received but could not be processed]';
        }
    }

    preprocessMessage(message) {
        // Clean up the message
        let cleanMessage = message.trim();
        
        // Remove excessive whitespace
        cleanMessage = cleanMessage.replace(/\\s+/g, ' ');
        
        // Remove some common WhatsApp formatting
        cleanMessage = cleanMessage.replace(/\\*([^*]+)\\*/g, '$1'); // Remove *bold*
        cleanMessage = cleanMessage.replace(/_([^_]+)_/g, '$1'); // Remove _italic_
        cleanMessage = cleanMessage.replace(/~([^~]+)~/g, '$1'); // Remove ~strikethrough~
        
        return cleanMessage;
    }
}

module.exports = MessageProcessor;
