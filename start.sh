#!/bin/bash

# WhatsApp Bot Startup Script

set -e

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
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

print_header() {
    echo -e "${BLUE}$1${NC}"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f ".env" ]; then
        print_error ".env file not found. Please run setup.sh first or copy .env.example to .env"
        exit 1
    fi
}

# Check if OpenAI API key is set
check_openai_key() {
    if ! grep -q "OPENAI_API_KEY=sk-" .env; then
        print_warning "OpenAI API key not set in .env file"
        print_warning "Please edit .env and set your OPENAI_API_KEY"
        exit 1
    fi
}

# Start backend
start_backend() {
    print_status "Starting Python backend..."
    
    if [ ! -d "venv" ]; then
        print_error "Virtual environment not found. Please run setup.sh first"
        exit 1
    fi
    
    source venv/bin/activate
    
    # Start backend from the project root, not the backend directory
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
    cd backend
    python main.py &
    backend_pid=$!
    cd ..
    
    print_status "Backend started with PID: $backend_pid"
    echo $backend_pid > .backend_pid
    
    # Wait for backend to start
    sleep 5
    
    # Check if backend is responding
    if curl -s http://localhost:8000/health > /dev/null; then
        print_status "Backend is responding"
    else
        print_error "Backend failed to start or is not responding"
        if [ -f ".backend_pid" ]; then
            backend_pid=$(cat .backend_pid)
            if ps -p $backend_pid > /dev/null; then
                kill $backend_pid
            fi
            rm .backend_pid
        fi
        exit 1
    fi
}

# Start frontend
start_frontend() {
    print_status "Starting WhatsApp frontend..."
    
    if [ ! -d "node_modules" ]; then
        print_error "Node.js dependencies not found. Please run setup.sh first"
        exit 1
    fi
    
    node index.js &
    frontend_pid=$!
    
    print_status "Frontend started with PID: $frontend_pid"
    echo $frontend_pid > .frontend_pid
}

# Stop services
stop_services() {
    print_status "Stopping services..."
    
    if [ -f ".backend_pid" ]; then
        backend_pid=$(cat .backend_pid)
        if ps -p $backend_pid > /dev/null; then
            kill $backend_pid
            print_status "Backend stopped"
        fi
        rm .backend_pid
    fi
    
    if [ -f ".frontend_pid" ]; then
        frontend_pid=$(cat .frontend_pid)
        if ps -p $frontend_pid > /dev/null; then
            kill $frontend_pid
            print_status "Frontend stopped"
        fi
        rm .frontend_pid
    fi
}

# Show status
show_status() {
    print_header "WhatsApp Bot Status"
    echo "=================="
    
    # Check backend
    if [ -f ".backend_pid" ]; then
        backend_pid=$(cat .backend_pid)
        if ps -p $backend_pid > /dev/null; then
            print_status "Backend running (PID: $backend_pid)"
        else
            print_error "Backend not running"
        fi
    else
        print_error "Backend not started"
    fi
    
    # Check frontend
    if [ -f ".frontend_pid" ]; then
        frontend_pid=$(cat .frontend_pid)
        if ps -p $frontend_pid > /dev/null; then
            print_status "Frontend running (PID: $frontend_pid)"
        else
            print_error "Frontend not running"
        fi
    else
        print_error "Frontend not started"
    fi
    
    # Check backend health
    if curl -s http://localhost:8000/health > /dev/null; then
        health_response=$(curl -s http://localhost:8000/health)
        functions_count=$(echo $health_response | grep -o '"functions":[0-9]*' | cut -d':' -f2)
        print_status "Backend healthy (${functions_count} functions loaded)"
    else
        print_error "Backend health check failed"
    fi
}

# Show logs
show_logs() {
    print_header "Recent Logs"
    echo "==========="
    
    if [ -f "logs/whatsapp-bot.log" ]; then
        echo "Frontend logs:"
        tail -20 logs/whatsapp-bot.log
        echo
    fi
    
    if [ -f "logs/error.log" ]; then
        echo "Error logs:"
        tail -10 logs/error.log
        echo
    fi
}

# Main function
main() {
    case "${1:-start}" in
        start)
            print_header "🚀 Starting WhatsApp Bot"
            echo "========================"
            check_env_file
            check_openai_key
            start_backend
            start_frontend
            echo
            print_status "WhatsApp Bot started successfully!"
            print_status "Scan the QR code that appears with your WhatsApp mobile app"
            print_status "Use './start.sh status' to check status"
            print_status "Use './start.sh stop' to stop the bot"
            print_status "Use './start.sh logs' to view logs"
            ;;
        stop)
            print_header "🛑 Stopping WhatsApp Bot"
            echo "========================"
            stop_services
            ;;
        restart)
            print_header "🔄 Restarting WhatsApp Bot"
            echo "=========================="
            stop_services
            sleep 2
            start_backend
            start_frontend
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|logs}"
            echo
            echo "Commands:"
            echo "  start   - Start the WhatsApp bot"
            echo "  stop    - Stop the WhatsApp bot"
            echo "  restart - Restart the WhatsApp bot"
            echo "  status  - Show bot status"
            echo "  logs    - Show recent logs"
            exit 1
            ;;
    esac
}

# Handle Ctrl+C
trap 'stop_services; exit' INT TERM

# Run main function
main "$@"
