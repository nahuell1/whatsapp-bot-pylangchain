/**
 * Configuration Module
 * 
 * Loads and exports all environment-based configuration settings for the WhatsApp bot.
 * Settings include backend connection, rate limiting, features, and access control.
 * 
 * @module config
 */

require('dotenv').config();

// Default values
const DEFAULT_BACKEND_URL = 'http://localhost:8000';
const DEFAULT_BACKEND_TIMEOUT = 30000;
const DEFAULT_MAX_MESSAGE_LENGTH = 10000;
const DEFAULT_LOG_LEVEL = 'info';
const DEFAULT_RATE_LIMIT_WINDOW = 60000;
const DEFAULT_RATE_LIMIT_MAX_REQUESTS = 10;
const DEFAULT_HEALTH_CHECK_INTERVAL = 300000;
const DEFAULT_MAX_RETRIES = 3;
const DEFAULT_RETRY_DELAY = 1000;

module.exports = {
    BACKEND_URL: process.env.BACKEND_URL || DEFAULT_BACKEND_URL,
    BACKEND_TIMEOUT: parseInt(process.env.BACKEND_TIMEOUT) || DEFAULT_BACKEND_TIMEOUT,
    
    WHATSAPP_SESSION_PATH: process.env.WHATSAPP_SESSION_PATH || './.wwebjs_auth',
    MAX_MESSAGE_LENGTH: parseInt(process.env.MAX_MESSAGE_LENGTH) || DEFAULT_MAX_MESSAGE_LENGTH,
    
    LOG_LEVEL: process.env.LOG_LEVEL || DEFAULT_LOG_LEVEL,
    
    RATE_LIMIT_WINDOW: parseInt(process.env.RATE_LIMIT_WINDOW) || DEFAULT_RATE_LIMIT_WINDOW,
    RATE_LIMIT_MAX_REQUESTS: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || DEFAULT_RATE_LIMIT_MAX_REQUESTS,
    
    ENABLE_GROUP_MESSAGES: process.env.ENABLE_GROUP_MESSAGES !== 'false',
    ENABLE_MEDIA_PROCESSING: process.env.ENABLE_MEDIA_PROCESSING === 'true',
    ENABLE_TYPING_INDICATOR: process.env.ENABLE_TYPING_INDICATOR !== 'false',
    
    HEALTH_CHECK_INTERVAL: parseInt(process.env.HEALTH_CHECK_INTERVAL) || DEFAULT_HEALTH_CHECK_INTERVAL,
    
    MAX_RETRIES: parseInt(process.env.MAX_RETRIES) || DEFAULT_MAX_RETRIES,
    RETRY_DELAY: parseInt(process.env.RETRY_DELAY) || DEFAULT_RETRY_DELAY,
    
    ALLOWED_USER_IDS: (process.env.ALLOWED_USER_IDS || '')
        .split(',')
        .map(s => s.trim())
        .filter(s => s.length > 0)
};
