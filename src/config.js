/**
 * Configuration settings for the WhatsApp bot
 */

require('dotenv').config();

module.exports = {
    // Backend configuration
    BACKEND_URL: process.env.BACKEND_URL || 'http://localhost:8000',
    BACKEND_TIMEOUT: parseInt(process.env.BACKEND_TIMEOUT) || 30000,
    
    // WhatsApp configuration
    WHATSAPP_SESSION_PATH: process.env.WHATSAPP_SESSION_PATH || './.wwebjs_auth',
    MAX_MESSAGE_LENGTH: parseInt(process.env.MAX_MESSAGE_LENGTH) || 10000,
    
    // Logging configuration
    LOG_LEVEL: process.env.LOG_LEVEL || 'info',
    
    // Rate limiting
    RATE_LIMIT_WINDOW: parseInt(process.env.RATE_LIMIT_WINDOW) || 60000, // 1 minute
    RATE_LIMIT_MAX_REQUESTS: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 10,
    
    // Features
    ENABLE_GROUP_MESSAGES: process.env.ENABLE_GROUP_MESSAGES === 'true',
    ENABLE_MEDIA_PROCESSING: process.env.ENABLE_MEDIA_PROCESSING === 'true',
    ENABLE_TYPING_INDICATOR: process.env.ENABLE_TYPING_INDICATOR !== 'false',
    
    // Health check
    HEALTH_CHECK_INTERVAL: parseInt(process.env.HEALTH_CHECK_INTERVAL) || 300000, // 5 minutes
    
    // Error handling
    MAX_RETRIES: parseInt(process.env.MAX_RETRIES) || 3,
    RETRY_DELAY: parseInt(process.env.RETRY_DELAY) || 1000,
    
    // Access control (comma separated user IDs / phone numbers without @c.us)
    ALLOWED_USER_IDS: (process.env.ALLOWED_USER_IDS || '')
        .split(',')
        .map(s => s.trim())
        .filter(s => s.length > 0)
};
