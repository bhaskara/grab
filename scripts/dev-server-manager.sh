#!/bin/bash

# Grab Game Development Server Manager
#
# NOTE: For local Mac development, prefer using honcho instead:
#
#   honcho start          (from the repo root)
#
# honcho starts both Flask and React together with color-coded, prefixed logs
# and clean Ctrl-C shutdown.  See the repo-root Procfile for details.
#
# This script remains useful for Linux/server environments where UFW firewall
# management is needed, or when you want to run the React dev server alone.
#
# Usage:
#   ./dev-server-manager.sh [--firewall]
#
# Options:
#   --firewall   Enable UFW firewall management (Linux server use only).
#                Without this flag the script works fine on macOS or any
#                environment where UFW is not installed.

set -e

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

MANAGE_FIREWALL="no"
for arg in "$@"; do
    case "$arg" in
        --firewall)
            MANAGE_FIREWALL="yes"
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: $0 [--firewall]"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Resolve the repo root relative to this script so the script works regardless
# of where it is invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WEB_DIR="$REPO_ROOT/web"

REACT_PORT=3000
FLASK_PORT=5001
SERVER_IP="165.232.153.59"  # External IP (only relevant when --firewall is used)
BACKUP_DIR="/tmp/firewall-backup-$(date +%s)"

# ---------------------------------------------------------------------------
# Process state
# ---------------------------------------------------------------------------

NPM_PID=""
FIREWALL_WAS_ACTIVE=""

# ---------------------------------------------------------------------------
# Colors for output
# ---------------------------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Port-checking helper (cross-platform: works on macOS and Linux)
# ---------------------------------------------------------------------------

# port_in_use PORT
# Returns 0 (true) if something is listening on PORT, 1 otherwise.
port_in_use() {
    local port="$1"
    lsof -iTCP:"$port" -sTCP:LISTEN -t >/dev/null 2>&1
}

# ---------------------------------------------------------------------------
# Firewall functions (only called when --firewall is active)
# ---------------------------------------------------------------------------

# Back up the current UFW state so we can restore it later.
backup_firewall() {
    print_status "Backing up current firewall configuration..."
    mkdir -p "$BACKUP_DIR"

    if sudo ufw status | grep -q "Status: active"; then
        FIREWALL_WAS_ACTIVE="yes"
        sudo ufw status numbered > "$BACKUP_DIR/ufw_rules.txt"
        print_status "Firewall was active, rules backed up to $BACKUP_DIR/ufw_rules.txt"
    else
        FIREWALL_WAS_ACTIVE="no"
        print_status "Firewall was inactive"
    fi
}

# Remove the rules we added and restore the previous firewall state.
restore_firewall() {
    print_status "Restoring original firewall configuration..."

    print_status "Removing development server ports from firewall..."

    sudo ufw --force delete allow $REACT_PORT/tcp > /dev/null 2>&1 || true
    print_status "Removed port $REACT_PORT rule"

    sudo ufw --force delete allow $FLASK_PORT/tcp > /dev/null 2>&1 || true
    print_status "Removed port $FLASK_PORT rule"

    if [ "$FIREWALL_WAS_ACTIVE" = "no" ]; then
        sudo ufw --force disable > /dev/null 2>&1
        print_status "Firewall disabled (was originally inactive)"
        rm -rf "$BACKUP_DIR" 2>/dev/null || true
    else
        print_status "Firewall kept active (was originally active)"
        print_status "SSH and other existing rules preserved"
    fi
}

# Open the necessary ports in UFW for development access.
setup_firewall() {
    print_status "Configuring firewall for development access..."

    # Ensure SSH is always allowed (safety first!)
    sudo ufw allow ssh > /dev/null 2>&1 || true
    print_status "Ensured SSH access is preserved"

    if [ "$FIREWALL_WAS_ACTIVE" = "no" ]; then
        sudo ufw --force enable > /dev/null 2>&1
        print_status "Enabled firewall (was originally inactive)"
    fi

    sudo ufw allow $REACT_PORT/tcp comment "React dev server" > /dev/null 2>&1
    print_status "Opened port $REACT_PORT for React dev server"

    sudo ufw allow $FLASK_PORT/tcp comment "Flask game server" > /dev/null 2>&1
    print_status "Opened port $FLASK_PORT for Flask game server"

    print_status "Current firewall status:"
    sudo ufw status numbered
}

# ---------------------------------------------------------------------------
# React server management
# ---------------------------------------------------------------------------

# Kill any running react-scripts start processes and free REACT_PORT.
cleanup_existing_react_processes() {
    print_status "Checking for existing React dev server processes..."

    local existing_pids
    existing_pids=$(ps aux | grep "react-scripts.*start" | grep -v grep | awk '{print $2}')

    if [ -n "$existing_pids" ]; then
        print_warning "Found existing React dev server processes. Cleaning up..."

        for pid in $existing_pids; do
            if kill -0 "$pid" 2>/dev/null; then
                print_status "Stopping React process (PID: $pid)"
                kill "$pid" 2>/dev/null || true
                sleep 2
                if kill -0 "$pid" 2>/dev/null; then
                    print_status "Force stopping React process (PID: $pid)"
                    kill -9 "$pid" 2>/dev/null || true
                fi
            fi
        done

        # Also kill anything still holding the port (lsof works on macOS + Linux)
        local port_pids
        port_pids=$(lsof -iTCP:"$REACT_PORT" -sTCP:LISTEN -t 2>/dev/null || true)
        if [ -n "$port_pids" ]; then
            for pid in $port_pids; do
                if kill -0 "$pid" 2>/dev/null; then
                    print_status "Stopping process holding port $REACT_PORT (PID: $pid)"
                    kill "$pid" 2>/dev/null || true
                    sleep 1
                    if kill -0 "$pid" 2>/dev/null; then
                        kill -9 "$pid" 2>/dev/null || true
                    fi
                fi
            done
        fi

        sleep 2
        print_success "Cleanup completed"
    else
        print_status "No existing React processes found"
    fi
}

# Start the React dev server in the background.
start_servers() {
    print_status "Starting development servers..."

    cleanup_existing_react_processes

    if [ ! -d "$WEB_DIR" ]; then
        print_error "Web directory not found: $WEB_DIR"
        return 1
    fi

    cd "$WEB_DIR"
    print_status "Starting React dev server on port $REACT_PORT..."

    BROWSER=none HOST=0.0.0.0 npm start > /tmp/react-dev.log 2>&1 &
    NPM_PID=$!

    print_status "React dev server starting (PID: $NPM_PID)..."
    print_status "Waiting for server to be ready..."

    local timeout=30
    local counter=0
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

# Stop the React dev server.
stop_servers() {
    print_status "Stopping development servers..."
    cleanup_existing_react_processes
    NPM_PID=""
}

# ---------------------------------------------------------------------------
# Connection info / status
# ---------------------------------------------------------------------------

# Print URLs for accessing the running servers.
show_connection_info() {
    echo ""
    print_success "Development servers are ready!"
    echo ""
    if [ "$MANAGE_FIREWALL" = "yes" ]; then
        print_status "Connect from an external machine using:"
        echo -e "  ${GREEN}React App:${NC}    http://$SERVER_IP:$REACT_PORT"
        echo -e "  ${GREEN}Flask Server:${NC} http://$SERVER_IP:$FLASK_PORT"
        echo ""
    fi
    print_status "Local access:"
    echo -e "  ${BLUE}React App:${NC}    http://localhost:$REACT_PORT"
    echo -e "  ${BLUE}Flask Server:${NC} http://localhost:$FLASK_PORT"
    echo ""
    print_warning "Remember to start your Flask server separately if you want to test the full stack!"
    print_warning "Run: python run.py (in a separate terminal)"
    echo ""
}

# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

handle_start() {
    if [ -n "$NPM_PID" ] && kill -0 "$NPM_PID" 2>/dev/null; then
        print_warning "Development servers are already running!"
        show_connection_info
        return
    fi

    print_status "Starting development environment..."

    if [ "$MANAGE_FIREWALL" = "yes" ]; then
        backup_firewall
        setup_firewall
    fi

    start_servers
    show_connection_info
}

handle_stop() {
    print_status "Stopping development environment..."

    stop_servers

    if [ "$MANAGE_FIREWALL" = "yes" ]; then
        restore_firewall
        print_success "Development environment stopped and firewall restored"
    else
        print_success "Development environment stopped"
    fi
}

handle_status() {
    echo ""
    print_status "=== Development Environment Status ==="

    # React dev server
    if [ -n "$NPM_PID" ] && kill -0 "$NPM_PID" 2>/dev/null; then
        print_success "React dev server: RUNNING (PID: $NPM_PID)"
        if [ "$MANAGE_FIREWALL" = "yes" ]; then
            echo -e "  External URL: ${GREEN}http://$SERVER_IP:$REACT_PORT${NC}"
        fi
    else
        print_error "React dev server: STOPPED"
    fi

    # Flask server
    if port_in_use "$FLASK_PORT"; then
        print_success "Flask server: RUNNING on port $FLASK_PORT"
        if [ "$MANAGE_FIREWALL" = "yes" ]; then
            echo -e "  External URL: ${GREEN}http://$SERVER_IP:$FLASK_PORT${NC}"
        fi
    else
        print_error "Flask server: STOPPED"
    fi

    # Firewall (only relevant when managing it)
    if [ "$MANAGE_FIREWALL" = "yes" ]; then
        if sudo ufw status | grep -q "Status: active"; then
            print_success "Firewall: ACTIVE"
            print_status "Open ports:"
            sudo ufw status | grep -E "(${REACT_PORT}|${FLASK_PORT})" | sed 's/^/  /'
        else
            print_warning "Firewall: INACTIVE"
        fi
    fi

    echo ""
}

# ---------------------------------------------------------------------------
# Signal handlers
# ---------------------------------------------------------------------------

cleanup() {
    print_warning "Received interrupt signal..."
    handle_stop
    exit 0
}

trap cleanup SIGINT SIGTERM

# ---------------------------------------------------------------------------
# Startup checks
# ---------------------------------------------------------------------------

if [ "$EUID" -eq 0 ]; then
    print_error "Don't run this script as root! It will use sudo when needed."
    exit 1
fi

# Verify required commands are available.  ufw is only required with --firewall.
required_cmds=(npm node lsof)
if [ "$MANAGE_FIREWALL" = "yes" ]; then
    required_cmds+=(ufw)
fi

for cmd in "${required_cmds[@]}"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        print_error "Required command not found: $cmd"
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Main interactive loop
# ---------------------------------------------------------------------------

main() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE} Grab Game Development Server Manager${NC}"
    if [ "$MANAGE_FIREWALL" = "yes" ]; then
        echo -e "${BLUE} (firewall management enabled)${NC}"
    fi
    echo -e "${BLUE}================================================${NC}"
    echo ""
    echo "Commands:"
    echo "  start  - Start React dev server$([ "$MANAGE_FIREWALL" = "yes" ] && echo " and open firewall")"
    echo "  stop   - Stop servers$([ "$MANAGE_FIREWALL" = "yes" ] && echo " and restore firewall")"
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
                echo "  start  - Start development servers$([ "$MANAGE_FIREWALL" = "yes" ] && echo " and configure firewall")"
                echo "  stop   - Stop servers$([ "$MANAGE_FIREWALL" = "yes" ] && echo " and restore original firewall settings")"
                echo "  status - Show current status of servers$([ "$MANAGE_FIREWALL" = "yes" ] && echo " and firewall")"
                echo "  exit   - Exit this script (will stop servers first)"
                echo ""
                ;;
            "exit"|"quit"|"q")
                if [ -n "$NPM_PID" ] && kill -0 "$NPM_PID" 2>/dev/null; then
                    print_status "Stopping servers before exit..."
                    handle_stop
                fi
                print_status "Goodbye!"
                break
                ;;
            "")
                # Empty input — continue
                ;;
            *)
                print_error "Unknown command: $command"
                echo "Type 'help' for available commands"
                ;;
        esac
    done
}

main
