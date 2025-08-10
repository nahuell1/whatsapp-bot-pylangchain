/**
 * WhatsApp Bot Frontend
 * Main entry point for the WhatsApp bot using whatsapp-web.js
 */

require('dotenv').config();
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const WhatsAppBot = require('./src/bot');
const logger = require('./src/utils/logger');

async function main() {
    logger.info('Starting WhatsApp Bot Frontend...');
    
    try {
        const chromePath = process.env.CHROME_PATH;
    if (chromePath) logger.info(`Usando navegador: ${chromePath}`);
        // Build puppeteer options
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
            puppeteerOpts.executablePath = chromePath; // only set if provided
        }
        // Initialize WhatsApp client
        const client = new Client({
            authStrategy: new LocalAuth({
                clientId: 'whatsapp-bot',
                dataPath: process.env.WHATSAPP_SESSION_PATH || './.wwebjs_auth'
            }),
            puppeteer: puppeteerOpts
        });

        // Initialize bot
        const bot = new WhatsAppBot(client);
        
        // Set up event handlers
        client.on('qr', (qr) => {
            logger.info('QR code received, scan with WhatsApp mobile app');
            qrcode.generate(qr, { small: true });
        });

        client.on('ready', () => {
            logger.info('WhatsApp client is ready!');
            logger.info(`Bot is connected and ready to receive messages`);
        });

        client.on('authenticated', () => {
            logger.info('WhatsApp client authenticated');
        });

        client.on('auth_failure', (msg) => {
            logger.error('Authentication failed:', msg);
        });

        client.on('disconnected', (reason) => {
            logger.warn('WhatsApp client disconnected:', reason);
        });

        // Start the client
        await client.initialize();
        
        // Graceful shutdown
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

    } catch (error) {
        logger.error('Error starting WhatsApp bot:', error);
        process.exit(1);
    }
}

main().catch(error => {
    logger.error('Unhandled error:', error);
    process.exit(1);
});
