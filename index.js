/**
 * WhatsApp Bot Frontend - Main Entry Point
 * 
 * Initializes WhatsApp client with whatsapp-web.js and connects to Python backend.
 * Handles authentication, QR code generation, and graceful shutdown.
 * 
 * @module index
 */

require('dotenv').config();
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const WhatsAppBot = require('./src/bot');
const logger = require('./src/utils/logger');
const config = require('./src/config');

// Constants
const CLIENT_ID = 'whatsapp-bot';
const READY_CHECK_INTERVAL_MS = 5000;
const READY_CHECK_TIMEOUT_MS = 60000;
const READY_WARNING_THRESHOLD_MS = 10000;

/**
 * Main application function
 * Initializes WhatsApp client and sets up event handlers
 */
async function main() {
    logger.info('Starting WhatsApp Bot Frontend...');
    
    try {
        logger.info(`Backend URL: ${config.BACKEND_URL}`);
        logger.info(`Allowed users: ${config.ALLOWED_USER_IDS.length > 0 ? config.ALLOWED_USER_IDS.join(',') : '(any)'}`);
        
        const chromePath = process.env.CHROME_PATH;
        if (chromePath) {
            logger.info(`Using custom browser: ${chromePath}`);
        }
        
        const puppeteerOpts = {
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        };
        if (chromePath) {
            puppeteerOpts.executablePath = chromePath;
        }
        
        const client = new Client({
            authStrategy: new LocalAuth({
                clientId: CLIENT_ID,
                dataPath: process.env.WHATSAPP_SESSION_PATH || './.wwebjs_auth'
            }),
            puppeteer: puppeteerOpts
        });
        
        setupEventHandlers(client);
        
        const bot = new WhatsAppBot(client);
        
        await client.initialize();
        
        setupGracefulShutdown(client);
        
    } catch (error) {
        logger.error('Error starting WhatsApp bot:', error);
        process.exit(1);
    }
}

/**
 * Set up WhatsApp client event handlers
 * @param {Client} client - WhatsApp client instance
 */
function setupEventHandlers(client) {
    client.on('qr', (qr) => {
        logger.info('QR code received, scan with WhatsApp mobile app');
        qrcode.generate(qr, { small: true });
    });

    client.on('ready', () => {
        logger.info('WhatsApp client is ready!');
        logger.info('Bot is connected and ready to receive messages');
    });

    let authenticatedAt = null;
    client.on('authenticated', () => {
        logger.info('✅ WhatsApp client authenticated');
        authenticatedAt = Date.now();
        
        const checkReadyInterval = setInterval(() => {
            const hasInfo = !!client.info;
            const hasMe = !!(client.info && client.info.me);
            logger.debug(`Client state: info=${hasInfo}, me=${hasMe}`);
            
            if (hasInfo && hasMe && Date.now() - authenticatedAt > READY_WARNING_THRESHOLD_MS) {
                logger.info('⚠️ Client appears ready but "ready" event has not fired. Messages should still work.');
                clearInterval(checkReadyInterval);
            }
        }, READY_CHECK_INTERVAL_MS);
        
        setTimeout(() => {
            clearInterval(checkReadyInterval);
            if (!client.info || !client.info.me) {
                logger.warn('⚠️ Client not ready 60s after authentication. Messages may not be received. Try restarting the container.');
            }
        }, READY_CHECK_TIMEOUT_MS);
    });

    client.on('auth_failure', (msg) => {
        logger.error('Authentication failed:', msg);
    });

    client.on('disconnected', (reason) => {
        logger.warn('WhatsApp client disconnected:', reason);
    });
}

/**
 * Set up graceful shutdown handlers
 * @param {Client} client - WhatsApp client instance
 */
function setupGracefulShutdown(client) {
    process.on('SIGINT', async () => {
        logger.info('Received SIGINT, shutting down gracefully...');
        await client.destroy();
        process.exit(0);
    });

    process.on('SIGTERM', async () => {
        logger.info('Received SIGTERM, shutting down gracefully...');
        await client.destroy();
        process.exit(0);
    });
}

main().catch(error => {
    logger.error('Unhandled error:', error);
    process.exit(1);
});
