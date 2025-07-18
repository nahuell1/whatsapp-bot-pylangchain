/**
 * Command Handler
 * Handles direct function calls with ! prefix
 */

const logger = require('./utils/logger');
const axios = require('axios');

class CommandHandler {
    constructor() {
        this.commandPrefix = '!';
        this.availableFunctions = new Map();
        this.backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
        this.functionMetadata = null;
        
        // Load available functions from backend
        this.loadAvailableFunctions();
    }

    async loadAvailableFunctions() {
        try {
            logger.debug('Loading available functions from backend...');
            const response = await axios.get(`${this.backendUrl}/functions`);
            
            if (response.data && response.data.functions) {
                this.functionMetadata = response.data.functions;
                
                // Build command map
                this.availableFunctions.clear();
                for (const [functionName, metadata] of Object.entries(this.functionMetadata)) {
                    this.availableFunctions.set(functionName, metadata);
                    logger.debug(`Registered command: !${functionName}`);
                }
                
                logger.info(`Loaded ${this.availableFunctions.size} available commands`);
            }
        } catch (error) {
            logger.error('Failed to load available functions:', error);
            // Fallback to hardcoded functions if backend is not available
            this.availableFunctions.set('weather', { name: 'weather', description: 'Get weather information' });
            this.availableFunctions.set('news', { name: 'news', description: 'Get latest news' });
            this.availableFunctions.set('system_info', { name: 'system_info', description: 'Get system information' });
        }
    }

    isCommand(message) {
        return message.startsWith(this.commandPrefix);
    }

    parseCommand(message) {
        // Remove the ! prefix
        const commandText = message.substring(1);
        
        // Split by spaces to get command and arguments
        const parts = commandText.split(/\s+/);
        const command = parts[0].toLowerCase();
        const args = parts.slice(1);
        
        return {
            command,
            args,
            originalText: commandText
        };
    }

    async executeCommand(message, userContext) {
        try {
            const { command, args, originalText } = this.parseCommand(message);
            
            logger.info(`Executing command: !${command} with args: ${args.join(' ')}`);
            
            // Check if command exists
            if (!this.availableFunctions.has(command)) {
                return {
                    success: false,
                    message: `❌ Comando desconocido: !${command}\n\n📋 Comandos disponibles:\n${this.getAvailableCommands()}`
                };
            }

            // Prepare parameters based on the function and arguments
            const parameters = this.prepareParameters(command, args);
            
            // Execute the function directly via backend
            const response = await axios.post(`${this.backendUrl}/execute-function`, {
                function_name: command,
                parameters: parameters,
                user_context: userContext
            });

            if (response.data.success) {
                return {
                    success: true,
                    message: response.data.result,
                    metadata: {
                        command: command,
                        args: args,
                        executionTime: response.data.execution_time
                    }
                };
            } else {
                return {
                    success: false,
                    message: `❌ Error ejecutando !${command}: ${response.data.error}`
                };
            }

        } catch (error) {
            logger.error('Error executing command:', error);
            return {
                success: false,
                message: `❌ Error interno ejecutando el comando: ${error.message}`
            };
        }
    }

    prepareParameters(command, args) {
        const parameters = {};
        
        if (!this.functionMetadata || !this.functionMetadata[command]) {
            logger.warn(`No metadata found for command: ${command}`);
            return parameters;
        }
        
        const commandInfo = this.functionMetadata[command].command_info;
        const parameterMapping = commandInfo.parameter_mapping || {};
        
        // Process parameter mapping
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
        
        // If no specific mapping and there are arguments, try to infer
        if (Object.keys(parameters).length === 0 && args.length > 0) {
            const functionParams = this.functionMetadata[command].parameters || {};
            const paramKeys = Object.keys(functionParams);
            
            if (paramKeys.length > 0) {
                const firstParam = paramKeys[0];
                parameters[firstParam] = args.join(' ');
            }
        }
        
        return parameters;
    }

    getAvailableCommands() {
        const commands = Array.from(this.availableFunctions.keys());
        return commands.map(cmd => `• !${cmd}`).join('\n');
    }

    getCommandHelp(command) {
        const functionInfo = this.availableFunctions.get(command);
        if (!functionInfo) {
            return `❌ Comando desconocido: !${command}`;
        }

        let help = `📋 **!${command}**\n`;
        help += `${functionInfo.description || 'No hay descripción disponible'}\n\n`;
        
        const commandInfo = functionInfo.command_info || {};
        
        // Add usage from command info
        if (commandInfo.usage) {
            help += `📝 **Uso:** ${commandInfo.usage}\n`;
        }
        
        // Add examples from command info
        if (commandInfo.examples && commandInfo.examples.length > 0) {
            help += `� **Ejemplos:**\n`;
            commandInfo.examples.forEach(example => {
                help += `• ${example}\n`;
            });
        }
        
        // If no command info, generate basic help from parameters
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
                
                help += `📝 **Uso:** ${usage}\n`;
                help += `📝 **Ejemplo:** !${command} ${requiredParams.map(() => 'valor').join(' ')}`;
            } else {
                help += `📝 **Uso:** !${command}\n`;
                help += `📝 **Ejemplo:** !${command}`;
            }
        }
        
        return help;
    }

    async handleHelpCommand(args) {
        if (args.length === 0) {
            // General help - generate examples dynamically
            const examples = [];
            for (const [command, functionInfo] of this.availableFunctions) {
                const commandInfo = functionInfo.command_info || {};
                if (commandInfo.examples && commandInfo.examples.length > 0) {
                    examples.push(commandInfo.examples[0]);
                } else {
                    examples.push(`!${command}`);
                }
            }
            
            return `🤖 **Sistema de Comandos Directos**\n\n` +
                   `Los comandos directos se ejecutan sin IA usando el prefijo !\n\n` +
                   `📋 **Comandos disponibles:**\n${this.getAvailableCommands()}\n\n` +
                   `💡 **Ejemplos:**\n${examples.slice(0, 5).map(ex => `• ${ex}`).join('\n')}\n\n` +
                   `❓ **Ayuda específica:** !help <comando>\n` +
                   `📝 **Ejemplo:** !help weather`;
        } else {
            // Specific command help
            const command = args[0].toLowerCase();
            return this.getCommandHelp(command);
        }
    }
}

module.exports = CommandHandler;
