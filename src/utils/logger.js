/**
 * Logger Module
 * 
 * Custom logger implementation with file and console output.
 * Supports multiple log levels (error, warn, info, debug) and automatic log rotation.
 * 
 * @module utils/logger
 */

const fs = require('fs');
const path = require('path');

require('dotenv').config();

// Constants
const DEFAULT_LOG_LEVEL = 'info';
const LOG_LEVELS = {
    ERROR: 0,
    WARN: 1,
    INFO: 2,
    DEBUG: 3
};
const DEFAULT_MAX_LOG_AGE = 7 * 24 * 60 * 60 * 1000;

/**
 * Logger class for structured logging with file and console output
 */
class Logger {
    constructor() {
        this.logLevel = (process.env.LOG_LEVEL || DEFAULT_LOG_LEVEL).toLowerCase();
        this.levels = {
            error: LOG_LEVELS.ERROR,
            warn: LOG_LEVELS.WARN,
            info: LOG_LEVELS.INFO,
            debug: LOG_LEVELS.DEBUG
        };
        
        const logsDir = path.join(process.cwd(), 'logs');
        if (!fs.existsSync(logsDir)) {
            fs.mkdirSync(logsDir, { recursive: true });
        }
        
        this.logFile = path.join(logsDir, 'whatsapp-bot.log');
        this.errorFile = path.join(logsDir, 'error.log');
    }

    /**
     * Check if log level should be logged
     * @param {string} level - Log level to check
     * @returns {boolean} True if level should be logged
     */
    shouldLog(level) {
        return this.levels[level] <= this.levels[this.logLevel.toLowerCase()];
    }

    /**
     * Format log message with timestamp and metadata
     * @param {string} level - Log level
     * @param {string} message - Log message
     * @param {*} extra - Additional data to log
     * @returns {string} Formatted log message
     */
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

    /**
     * Write log message to file
     * @param {string} message - Formatted log message
     * @param {boolean} isError - Whether this is an error log
     */
    writeToFile(message, isError = false) {
        try {
            const file = isError ? this.errorFile : this.logFile;
            const dir = path.dirname(file);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
            fs.appendFileSync(file, message + '\n');
        } catch (error) {
            console.error('Failed to write to log file:', error);
            console.error('Target file:', isError ? this.errorFile : this.logFile);
            console.error('Message:', message);
        }
    }

    /**
     * Log message at specified level
     * @param {string} level - Log level
     * @param {string} message - Log message
     * @param {*} extra - Additional data to log
     */
    log(level, message, extra = null) {
        if (!this.shouldLog(level)) {
            return;
        }

        const formattedMessage = this.formatMessage(level, message, extra);
        
        if (level === 'error') {
            console.error(formattedMessage);
        } else if (level === 'warn') {
            console.warn(formattedMessage);
        } else if (level === 'debug') {
            console.debug(formattedMessage);
        } else {
            console.log(formattedMessage);
        }
        
        this.writeToFile(formattedMessage, level === 'error');
    }

    /**
     * Log error message
     * @param {string} message - Error message
     * @param {*} extra - Additional error data
     */
    error(message, extra = null) {
        this.log('error', message, extra);
    }

    /**
     * Log warning message
     * @param {string} message - Warning message
     * @param {*} extra - Additional warning data
     */
    warn(message, extra = null) {
        this.log('warn', message, extra);
    }

    /**
     * Log info message
     * @param {string} message - Info message
     * @param {*} extra - Additional info data
     */
    info(message, extra = null) {
        this.log('info', message, extra);
    }

    /**
     * Log debug message
     * @param {string} message - Debug message
     * @param {*} extra - Additional debug data
     */
    debug(message, extra = null) {
        this.log('debug', message, extra);
    }

    /**
     * Clean up old log files
     * @param {number} maxAge - Maximum age of log files in milliseconds
     */
    cleanup(maxAge = DEFAULT_MAX_LOG_AGE) {
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
