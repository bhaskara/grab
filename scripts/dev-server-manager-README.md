# Development Server Manager

This script (`dev-server-manager.sh`) manages the React development server and firewall settings to allow external access from your laptop.

## Usage

1. **Start the script in a separate terminal:**
   ```bash
   ./dev-server-manager.sh
   ```

2. **Available commands:**
   - `start` - Starts React dev server and opens firewall ports
   - `stop` - Stops servers and restores original firewall settings  
   - `status` - Shows current status of servers and firewall
   - `help` - Shows help information
   - `exit` - Exits script (stops servers first if running)

## What it does when you type "start":

1. **Backs up current firewall configuration**
2. **Opens firewall ports:**
   - Port 3000 (React dev server)
   - Port 5000 (Flask game server)
3. **Starts React dev server** bound to all interfaces (0.0.0.0)
4. **Displays connection URLs** for your external laptop:
   - React App: `http://165.232.153.59:3000`
   - Flask Server: `http://165.232.153.59:5000`

## What it does when you type "stop":

1. **Stops the React dev server**
2. **Restores original firewall settings**
3. **Cleans up temporary files**

## Important Notes:

- **The script does NOT start your Flask game server** - you need to run `python run.py` separately if you want to test the full stack
- **External URLs for your laptop:**
  - React App: `http://165.232.153.59:3000`
  - Flask Server: `http://165.232.153.59:5000` (if you start it separately)
- **Local URLs (on the server):**
  - React App: `http://localhost:3000`
  - Flask Server: `http://localhost:5000`

## Security:

- **🔒 SSH-Safe**: The script NEVER removes SSH access - it explicitly preserves SSH rules
- **🎯 Selective port management**: Only adds/removes the specific development ports (3000, 5000)
- **🛡️ Preserves existing rules**: Never resets your entire firewall configuration  
- **🔄 Safe restoration**: When you "stop", it only removes the development ports it added
- **👤 Minimal privileges**: Uses sudo only for firewall commands, runs as regular user otherwise

## Troubleshooting:

- **Check status:** Use the `status` command to see what's running
- **React server logs:** Check `/tmp/react-dev.log` for React server output
- **Manual cleanup:** If something goes wrong, you can manually kill React processes with: `pkill -f "react-scripts start"`
- **Firewall reset:** If needed, manually reset firewall with: `sudo ufw --force reset`

## Example Session:

```
$ ./dev-server-manager.sh
================================================
 Grab Game Development Server Manager
================================================

Commands:
  start  - Start React dev server and open firewall
  stop   - Stop servers and restore firewall
  status - Show current status
  help   - Show this help
  exit   - Exit this script

dev-server> start
[INFO] Starting development environment...
[INFO] Backing up current firewall configuration...
[INFO] Configuring firewall for development access...
[INFO] Opened port 3000 for React dev server
[INFO] Opened port 5000 for Flask game server
[INFO] Starting React dev server on port 3000...
[INFO] React dev server starting (PID: 12345)...
[SUCCESS] React dev server is ready!

🚀 Development servers are ready!

Connect from your external laptop using:
  React App:    http://165.232.153.59:3000
  Flask Server: http://165.232.153.59:5000

dev-server> stop
[INFO] Stopping development environment...
[INFO] Stopping React dev server (PID: 12345)...
[SUCCESS] React dev server stopped
[INFO] Restoring original firewall configuration...
[SUCCESS] Development environment stopped and firewall restored

dev-server> exit
[INFO] Goodbye!
```