#!/bin/bash

# Grab Game Development Server Manager
# Manages React dev server and firewall settings for external access

set -e

# Configuration
WEB_DIR="/home/bhaskara/grab/web"
REACT_PORT=3000
FLASK_PORT=5000
SERVER_IP="165.232.153.59"  # Primary external IP
BACKUP_DIR="/tmp/firewall-backup-$(date +%s)"

# Process IDs
NPM_PID=""
FIREWALL_WAS_ACTIVE=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to backup current firewall state
backup_firewall() {
    print_status "Backing up current firewall configuration..."
    mkdir -p "$BACKUP_DIR"
    
    # Check if UFW is active
    if sudo ufw status | grep -q "Status: active"; then
        FIREWALL_WAS_ACTIVE="yes"
        sudo ufw status numbered > "$BACKUP_DIR/ufw_rules.txt"
        print_status "Firewall was active, rules backed up to $BACKUP_DIR/ufw_rules.txt"
    else
        FIREWALL_WAS_ACTIVE="no"
        print_status "Firewall was inactive"
    fi
}

# Function to restore firewall state
restore_firewall() {
    print_status "Restoring original firewall configuration..."
    
    # Only remove the specific rules we added, don't reset everything!
    print_status "Removing development server ports from firewall..."
    
    # Remove React dev server port rule
    sudo ufw --force delete allow $REACT_PORT/tcp > /dev/null 2>&1 || true
    print_status "Removed port $REACT_PORT rule"
    
    # Remove Flask server port rule  
    sudo ufw --force delete allow $FLASK_PORT/tcp > /dev/null 2>&1 || true
    print_status "Removed port $FLASK_PORT rule"
    
    # If firewall was originally inactive, disable it
    if [ "$FIREWALL_WAS_ACTIVE" = "no" ]; then
        sudo ufw --force disable > /dev/null 2>&1
        print_status "Firewall disabled (was originally inactive)"
    else
        print_status "Firewall kept active (was originally active)"
        print_status "SSH and other existing rules preserved"
    fi
    
    # Clean up backup directory if not needed
    if [ "$FIREWALL_WAS_ACTIVE" = "no" ]; then
        rm -rf "$BACKUP_DIR" 2>/dev/null || true
    fi
}

# Function to configure firewall for development
setup_firewall() {
    print_status "Configuring firewall for development access..."
    
    # Ensure SSH is always allowed (safety first!)
    sudo ufw allow ssh > /dev/null 2>&1 || true
    print_status "Ensured SSH access is preserved"
    
    # Enable UFW if not already enabled
    if [ "$FIREWALL_WAS_ACTIVE" = "no" ]; then
        sudo ufw --force enable > /dev/null 2>&1
        print_status "Enabled firewall (was originally inactive)"
    fi
    
    # Allow React dev server port
    sudo ufw allow $REACT_PORT/tcp comment "React dev server" > /dev/null 2>&1
    print_status "Opened port $REACT_PORT for React dev server"
    
    # Allow Flask server port (if running)
    sudo ufw allow $FLASK_PORT/tcp comment "Flask game server" > /dev/null 2>&1
    print_status "Opened port $FLASK_PORT for Flask game server"
    
    # Show current status
    print_status "Current firewall status:"
    sudo ufw status numbered
}

# Function to start the development servers
start_servers() {
    print_status "Starting development servers..."
    
    # Check if web directory exists
    if [ ! -d "$WEB_DIR" ]; then
        print_error "Web directory not found: $WEB_DIR"
        return 1
    fi
    
    # Start React dev server in background
    cd "$WEB_DIR"
    print_status "Starting React dev server on port $REACT_PORT..."
    
    # Start npm in background and capture PID
    BROWSER=none HOST=0.0.0.0 npm start > /tmp/react-dev.log 2>&1 &
    NPM_PID=$!
    
    print_status "React dev server starting (PID: $NPM_PID)..."
    print_status "Waiting for server to be ready..."
    
    # Wait for server to start (check log file)
    timeout=30
    counter=0
    while [ $counter -lt $timeout ]; do
        if grep -q "webpack compiled" /tmp/react-dev.log 2>/dev/null || 
           grep -q "compiled successfully" /tmp/react-dev.log 2>/dev/null; then
            break
        fi
        sleep 1
        counter=$((counter + 1))
        if [ $((counter % 5)) -eq 0 ]; then
            print_status "Still waiting for React dev server... ($counter/$timeout)"
        fi
    done
    
    if [ $counter -ge $timeout ]; then
        print_warning "React dev server may not have started properly. Check /tmp/react-dev.log"
    else
        print_success "React dev server is ready!"
    fi
}

# Function to stop the development servers
stop_servers() {
    print_status "Stopping development servers..."
    
    if [ -n "$NPM_PID" ] && kill -0 $NPM_PID 2>/dev/null; then
        print_status "Stopping React dev server (PID: $NPM_PID)..."
        kill $NPM_PID
        wait $NPM_PID 2>/dev/null || true
        print_success "React dev server stopped"
    else
        # Try to kill any remaining npm/node processes for this project
        pkill -f "react-scripts start" 2>/dev/null || true
        print_status "Cleaned up any remaining React dev server processes"
    fi
    
    NPM_PID=""
}

# Function to show connection information
show_connection_info() {
    echo ""
    print_success "🚀 Development servers are ready!"
    echo ""
    print_status "Connect from your external laptop using:"
    echo -e "  ${GREEN}React App:${NC}    http://$SERVER_IP:$REACT_PORT"
    echo -e "  ${GREEN}Flask Server:${NC} http://$SERVER_IP:$FLASK_PORT"
    echo ""
    print_status "Local access (on this server):"
    echo -e "  ${BLUE}React App:${NC}    http://localhost:$REACT_PORT"
    echo -e "  ${BLUE}Flask Server:${NC} http://localhost:$FLASK_PORT"
    echo ""
    print_warning "Remember to start your Flask server separately if you want to test the full stack!"
    print_warning "Run: python run.py (in a separate terminal)"
    echo ""
}

# Function to handle start command
handle_start() {
    if [ -n "$NPM_PID" ] && kill -0 $NPM_PID 2>/dev/null; then
        print_warning "Development servers are already running!"
        show_connection_info
        return
    fi
    
    print_status "🚀 Starting development environment..."
    
    backup_firewall
    setup_firewall
    start_servers
    show_connection_info
}

# Function to handle stop command
handle_stop() {
    print_status "🛑 Stopping development environment..."
    
    stop_servers
    restore_firewall
    
    print_success "Development environment stopped and firewall restored"
    
    # Clean up backup if firewall was originally inactive
    if [ "$FIREWALL_WAS_ACTIVE" = "no" ]; then
        rm -rf "$BACKUP_DIR" 2>/dev/null || true
    fi
}

# Function to handle status command
handle_status() {
    echo ""
    print_status "=== Development Environment Status ==="
    
    # Check React dev server
    if [ -n "$NPM_PID" ] && kill -0 $NPM_PID 2>/dev/null; then
        print_success "React dev server: RUNNING (PID: $NPM_PID)"
        echo -e "  External URL: ${GREEN}http://$SERVER_IP:$REACT_PORT${NC}"
    else
        print_error "React dev server: STOPPED"
    fi
    
    # Check Flask server
    if netstat -ln 2>/dev/null | grep -q ":$FLASK_PORT "; then
        print_success "Flask server: RUNNING on port $FLASK_PORT"
        echo -e "  External URL: ${GREEN}http://$SERVER_IP:$FLASK_PORT${NC}"
    else
        print_error "Flask server: STOPPED"
    fi
    
    # Check firewall
    if sudo ufw status | grep -q "Status: active"; then
        print_success "Firewall: ACTIVE"
        print_status "Open ports:"
        sudo ufw status | grep -E "(3000|5000)" | sed 's/^/  /'
    else
        print_warning "Firewall: INACTIVE"
    fi
    echo ""
}

# Signal handlers for clean shutdown
cleanup() {
    print_warning "Received interrupt signal..."
    handle_stop
    exit 0
}

trap cleanup SIGINT SIGTERM

# Main interactive loop
main() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE} Grab Game Development Server Manager${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo ""
    echo "Commands:"
    echo "  start  - Start React dev server and open firewall"
    echo "  stop   - Stop servers and restore firewall"
    echo "  status - Show current status"
    echo "  help   - Show this help"
    echo "  exit   - Exit this script"
    echo ""
    
    while true; do
        echo -n "dev-server> "
        read -r command
        
        case "$command" in
            "start")
                handle_start
                ;;
            "stop")
                handle_stop
                ;;
            "status")
                handle_status
                ;;
            "help")
                echo ""
                echo "Available commands:"
                echo "  start  - Start development servers and configure firewall"
                echo "  stop   - Stop servers and restore original firewall settings"
                echo "  status - Show current status of servers and firewall"
                echo "  exit   - Exit this script (will stop servers first)"
                echo ""
                ;;
            "exit"|"quit"|"q")
                if [ -n "$NPM_PID" ] && kill -0 $NPM_PID 2>/dev/null; then
                    print_status "Stopping servers before exit..."
                    handle_stop
                fi
                print_status "Goodbye!"
                break
                ;;
            "")
                # Empty input, just continue
                ;;
            *)
                print_error "Unknown command: $command"
                echo "Type 'help' for available commands"
                ;;
        esac
    done
}

# Check if script is run with proper permissions
if [ "$EUID" -eq 0 ]; then
    print_error "Don't run this script as root! It will use sudo when needed."
    exit 1
fi

# Check if required commands are available
for cmd in ufw npm node; do
    if ! command -v $cmd >/dev/null 2>&1; then
        print_error "Required command not found: $cmd"
        exit 1
    fi
done

# Start the interactive session
main