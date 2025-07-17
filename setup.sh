#!/bin/bash

# WhatsApp Bot Setup Script
# This script sets up the WhatsApp bot environment

set -e

echo "🚀 Setting up WhatsApp Bot with LangChain..."

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.9 or higher."
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2)
    print_status "Python version: $python_version"
}

# Check if Node.js is installed
check_nodejs() {
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js 18 or higher."
        exit 1
    fi
    
    node_version=$(node --version)
    print_status "Node.js version: $node_version"
}

# Check if npm is installed
check_npm() {
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install npm."
        exit 1
    fi
    
    npm_version=$(npm --version)
    print_status "npm version: $npm_version"
}

# Create virtual environment
setup_python_env() {
    print_status "Setting up Python environment..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_status "Created virtual environment"
    fi
    
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    pip install -r requirements.txt
    
    print_status "Python dependencies installed"
}

# Install Node.js dependencies
setup_nodejs_env() {
    print_status "Setting up Node.js environment..."
    
    npm install
    
    print_status "Node.js dependencies installed"
}

# Setup environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        print_warning "Created .env file from template. Please edit it with your configuration."
        print_warning "You need to set your OPENAI_API_KEY and other settings."
    else
        print_status "Environment file already exists"
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p backend/functions
    mkdir -p tests
    
    print_status "Directories created"
}

# Run tests
run_tests() {
    print_status "Running tests..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Run Python tests
    if [ -f "tests/test_backend.py" ]; then
        python -m pytest tests/ -v
    else
        print_warning "No Python tests found"
    fi
    
    # Run Node.js tests
    if [ -f "package.json" ] && grep -q "test" package.json; then
        npm test
    else
        print_warning "No Node.js tests configured"
    fi
}

# Main setup function
main() {
    echo "🔧 WhatsApp Bot Setup"
    echo "===================="
    echo
    
    # Check prerequisites
    check_python
    check_nodejs
    check_npm
    
    # Setup environments
    setup_python_env
    setup_nodejs_env
    
    # Setup configuration
    setup_environment
    create_directories
    
    echo
    print_status "Setup completed successfully!"
    echo
    echo "📋 Next steps:"
    echo "1. Edit the .env file with your OpenAI API key and other settings"
    echo "2. Start the backend: python backend/main.py"
    echo "3. Start the frontend: npm start"
    echo "4. Scan the QR code with WhatsApp"
    echo
    echo "📚 Documentation: README.md"
    echo "🐛 Issues: Check the logs/ directory for troubleshooting"
}

# Run main function
main "$@"
