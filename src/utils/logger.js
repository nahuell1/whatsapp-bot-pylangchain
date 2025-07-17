/**
 * Logger utility for the WhatsApp bot
 */

const fs = require('fs');
const path = require('path');

// Load environment variables
require('dotenv').config();

class Logger {
    constructor() {
        this.logLevel = (process.env.LOG_LEVEL || 'info').toLowerCase();
        this.levels = {
            error: 0,
            warn: 1,
            info: 2,
            debug: 3
        };
        
        // Create logs directory if it doesn't exist
        const logsDir = path.join(process.cwd(), 'logs');
        if (!fs.existsSync(logsDir)) {
            fs.mkdirSync(logsDir, { recursive: true });
        }
        
        this.logFile = path.join(logsDir, 'whatsapp-bot.log');
        this.errorFile = path.join(logsDir, 'error.log');
    }

    shouldLog(level) {
        return this.levels[level] <= this.levels[this.logLevel.toLowerCase()];
    }

    formatMessage(level, message, extra = null) {
        const timestamp = new Date().toISOString();
        const processId = process.pid;
        let logMessage = `[${timestamp}] [${processId}] [${level.toUpperCase()}] ${message}`;
        
        if (extra) {
            if (extra instanceof Error) {
                logMessage += `\n${extra.stack}`;
            } else if (typeof extra === 'object') {
                logMessage += `\n${JSON.stringify(extra, null, 2)}`;
            } else {
                logMessage += ` ${extra}`;
            }
        }
        
        return logMessage;
    }

    writeToFile(message, isError = false) {
        try {
            const file = isError ? this.errorFile : this.logFile;
            // Ensure the directory exists
            const dir = path.dirname(file);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
            // Write synchronously to ensure logs are written immediately
            fs.appendFileSync(file, message + '\n');
        } catch (error) {
            console.error('Failed to write to log file:', error);
            console.error('Target file:', isError ? this.errorFile : this.logFile);
            console.error('Message:', message);
        }
    }

    log(level, message, extra = null) {
        if (!this.shouldLog(level)) {
            return;
        }

        const formattedMessage = this.formatMessage(level, message, extra);
        
        // Write to console first
        if (level === 'error') {
            console.error(formattedMessage);
        } else if (level === 'warn') {
            console.warn(formattedMessage);
        } else if (level === 'debug') {
            console.debug(formattedMessage);
        } else {
            console.log(formattedMessage);
        }
        
        // Then write to file
        this.writeToFile(formattedMessage, level === 'error');
    }

    error(message, extra = null) {
        this.log('error', message, extra);
    }

    warn(message, extra = null) {
        this.log('warn', message, extra);
    }

    info(message, extra = null) {
        this.log('info', message, extra);
    }

    debug(message, extra = null) {
        this.log('debug', message, extra);
    }

    // Clean up old log files
    cleanup(maxAge = 7 * 24 * 60 * 60 * 1000) { // 7 days default
        try {
            const logsDir = path.dirname(this.logFile);
            const files = fs.readdirSync(logsDir);
            
            files.forEach(file => {
                const filePath = path.join(logsDir, file);
                const stats = fs.statSync(filePath);
                
                if (Date.now() - stats.mtime.getTime() > maxAge) {
                    fs.unlinkSync(filePath);
                    this.info(`Cleaned up old log file: ${file}`);
                }
            });
        } catch (error) {
            this.error('Failed to cleanup log files:', error);
        }
    }
}

module.exports = new Logger();
