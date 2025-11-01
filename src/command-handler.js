/**
 * Command Handler Module
 * 
 * Handles direct function calls with ! prefix syntax.
 * Loads available functions from backend, manages command aliases,
 * and provides help documentation.
 * 
 * @module command-handler
 */

const logger = require('./utils/logger');
const axios = require('axios');

// Constants
const COMMAND_PREFIX = '!';
const DEFAULT_BACKEND_URL = 'http://localhost:8000';
const MAX_HELP_EXAMPLES = 5;

/**
 * Command handler class for processing direct function calls
 */
class CommandHandler {
    constructor() {
        this.commandPrefix = COMMAND_PREFIX;
        this.availableFunctions = new Map();
        this.backendUrl = process.env.BACKEND_URL || DEFAULT_BACKEND_URL;
        this.functionMetadata = null;
        
        this.loadAvailableFunctions();
    }

    /**
     * Load available functions from backend API
     */
    async loadAvailableFunctions() {
        try {
            logger.debug('Loading available functions from backend...');
            const response = await axios.get(`${this.backendUrl}/functions`);
            
            if (response.data && response.data.functions) {
                this.functionMetadata = response.data.functions;
                
                this.availableFunctions.clear();
                for (const [functionName, metadata] of Object.entries(this.functionMetadata)) {
                    this.availableFunctions.set(functionName, metadata);
                    logger.debug(`Registered command: !${functionName}`);
                    
                    if (metadata.command_info && metadata.command_info.aliases) {
                        for (const alias of metadata.command_info.aliases) {
                            this.availableFunctions.set(alias, metadata);
                            logger.debug(`Registered alias: !${alias} -> ${functionName}`);
                        }
                    }
                }
                
                logger.info(`Loaded ${Object.keys(this.functionMetadata).length} functions with ${this.availableFunctions.size} total commands (including aliases)`);
            }
        } catch (error) {
            logger.error('Failed to load available functions:', error);
            this.availableFunctions.set('weather', { name: 'weather', description: 'Get weather information' });
            this.availableFunctions.set('news', { name: 'news', description: 'Get latest news' });
            this.availableFunctions.set('system_info', { name: 'system_info', description: 'Get system information' });
        }
    }

    /**
     * Check if message is a command
     * @param {string} message - Message text
     * @returns {boolean} True if message starts with command prefix
     */
    isCommand(message) {
        return message.startsWith(this.commandPrefix);
    }

    /**
     * Parse command from message
     * @param {string} message - Command message
     * @returns {Object} Parsed command object with command, args, and originalText
     */
    parseCommand(message) {
        const commandText = message.substring(1);
        const parts = commandText.split(/\s+/);
        const command = parts[0].toLowerCase();
        const args = parts.slice(1);
        
        return {
            command,
            args,
            originalText: commandText
        };
    }

    /**
     * Execute command by calling backend
     * @param {string} message - Command message
     * @param {Object} userContext - User context information
     * @returns {Promise<Object>} Execution result
     */
    async executeCommand(message, userContext) {
        try {
            const { command, args } = this.parseCommand(message);
            
            logger.info(`Executing command: !${command} with args: ${args.join(' ')}`);
            
            if (!this.availableFunctions.has(command)) {
                return {
                    success: false,
                    message: `Unknown command: !${command}\n\nAvailable commands:\n${this.getAvailableCommands()}`
                };
            }

            const parameters = this.prepareParameters(command, args);
            const functionMetadata = this.availableFunctions.get(command);
            const actualFunctionName = functionMetadata.name;
            
            const response = await axios.post(`${this.backendUrl}/execute-function`, {
                function_name: actualFunctionName,
                parameters: parameters,
                user_context: userContext
            });

            if (response.data.success) {
                const result = {
                    success: true,
                    message: response.data.result,
                    metadata: {
                        command: command,
                        function_name: actualFunctionName,
                        args: args,
                        executionTime: response.data.execution_time
                    }
                };
                
                // Check if there are images in the response
                // Images are nested in metadata.result.successful_captures
                if (response.data.metadata && response.data.metadata.result && response.data.metadata.result.successful_captures) {
                    const successfulCaptures = response.data.metadata.result.successful_captures;
                    const imagesWithData = successfulCaptures.filter(capture => capture.image_data);
                    
                    if (imagesWithData.length > 0) {
                        result.image_data = imagesWithData;
                        logger.debug(`Found ${imagesWithData.length} images in command response`);
                    }
                }

                // Single camera function (or any function returning single image_data)
                if (!result.image_data && response.data.metadata && response.data.metadata.result && response.data.metadata.result.image_data) {
                    const singleImage = response.data.metadata.result.image_data;
                    if (singleImage) {
                        result.image_data = [{ image_data: singleImage, camera_name: response.data.metadata.result.camera_name || 'camera' }];
                        logger.debug('Added single camera image from metadata.result.image_data');
                    }
                }
                
                return result;
            } else {
                return {
                    success: false,
                    message: `Error executing !${command}: ${response.data.error}`
                };
            }

        } catch (error) {
            logger.error('Error executing command:', error);
            return {
                success: false,
                message: `Internal error executing command: ${error.message}`
            };
        }
    }

    /**
     * Prepare function parameters from command arguments
     * @param {string} command - Command name
     * @param {Array<string>} args - Command arguments
     * @returns {Object} Prepared parameters
     */
    prepareParameters(command, args) {
        const parameters = {};
        let meta = (this.functionMetadata && this.functionMetadata[command]) || this.availableFunctions.get(command);
        if (!meta) {
            logger.warn(`No metadata found for command or alias: ${command}`);
            return parameters;
        }
        const commandInfo = meta.command_info || {};
        const parameterMapping = commandInfo.parameter_mapping || {};
        
        for (const [paramName, mappingType] of Object.entries(parameterMapping)) {
            switch (mappingType) {
                case 'join_args':
                    if (args.length > 0) {
                        parameters[paramName] = args.join(' ');
                    }
                    break;
                    
                case 'first_arg':
                    if (args.length > 0) {
                        parameters[paramName] = args[0];
                    }
                    break;
                    
                case 'second_arg':
                    if (args.length > 1) {
                        parameters[paramName] = args[1];
                    }
                    break;
                    
                case 'all_args':
                    parameters[paramName] = args;
                    break;
                    
                default:
                    logger.warn(`Unknown parameter mapping type: ${mappingType}`);
                    break;
            }
        }
        
        if (Object.keys(parameters).length === 0 && args.length > 0) {
            const functionParams = meta.parameters || {};
            const paramKeys = Object.keys(functionParams);
            
            if (paramKeys.length > 0) {
                const firstParam = paramKeys[0];
                parameters[firstParam] = args.join(' ');
            }
        }
        
        return parameters;
    }

    /**
     * Get list of available commands
     * @returns {string} Formatted list of commands
     */
    getAvailableCommands() {
        const commands = Array.from(this.availableFunctions.keys());
        return commands.map(cmd => `- !${cmd}`).join('\n');
    }

    /**
     * Get help text for specific command
     * @param {string} command - Command name
     * @returns {string} Formatted help text
     */
    getCommandHelp(command) {
        const functionInfo = this.availableFunctions.get(command);
        if (!functionInfo) {
            return `Unknown command: !${command}`;
        }

        let help = `Command: !${command}\n`;
        help += `${functionInfo.description || 'No description available'}\n\n`;
        
        const commandInfo = functionInfo.command_info || {};
        
        if (commandInfo.usage) {
            help += `Usage: ${commandInfo.usage}\n`;
        }
        
        if (commandInfo.examples && commandInfo.examples.length > 0) {
            help += `Examples:\n`;
            commandInfo.examples.forEach(example => {
                help += `- ${example}\n`;
            });
        }
        
        if (!commandInfo.usage && !commandInfo.examples) {
            const parameters = functionInfo.parameters || {};
            const paramKeys = Object.keys(parameters);
            
            if (paramKeys.length > 0) {
                const requiredParams = paramKeys.filter(key => parameters[key].required);
                const optionalParams = paramKeys.filter(key => !parameters[key].required);
                
                let usage = `!${command}`;
                if (requiredParams.length > 0) {
                    usage += ` <${requiredParams.join('> <')}>`;
                }
                if (optionalParams.length > 0) {
                    usage += ` [${optionalParams.join('] [')}]`;
                }
                
                help += `Usage: ${usage}\n`;
                help += `Example: !${command} ${requiredParams.map(() => 'value').join(' ')}`;
            } else {
                help += `Usage: !${command}\n`;
                help += `Example: !${command}`;
            }
        }
        
        return help;
    }

    /**
     * Handle help command
     * @param {Array<string>} args - Command arguments
     * @returns {Promise<string>} Help text
     */
    async handleHelpCommand(args) {
        if (args.length === 0) {
            const examples = [];
            for (const [command, functionInfo] of this.availableFunctions) {
                const commandInfo = functionInfo.command_info || {};
                if (commandInfo.examples && commandInfo.examples.length > 0) {
                    examples.push(commandInfo.examples[0]);
                } else {
                    examples.push(`!${command}`);
                }
            }
            
            return `Direct Command System\n\n` +
                   `Direct commands execute without AI using ! prefix\n\n` +
                   `Available commands:\n${this.getAvailableCommands()}\n\n` +
                   `Examples:\n${examples.slice(0, MAX_HELP_EXAMPLES).map(ex => `- ${ex}`).join('\n')}\n\n` +
                   `Specific help: !help <command>\n` +
                   `Example: !help weather`;
        } else {
            const command = args[0].toLowerCase();
            return this.getCommandHelp(command);
        }
    }
}

module.exports = CommandHandler;
