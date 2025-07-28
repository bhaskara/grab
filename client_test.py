#!/usr/bin/env python3
"""
Standalone integration test for client-server interaction.

This script tests the full flow:
1. Start the Grab server in the background
2. Multiple clients connect and authenticate
3. Client A creates and joins a game
4. Client B joins the same game
5. Client A starts the game
6. Both clients make moves
7. Verify everything works end-to-end

This is NOT part of the pytest suite but is a manual integration test
to catch real-world client-server issues.

All subprocess outputs are written to temporary files for easier debugging.
"""

import subprocess
import time
import signal
import os
import sys
import requests
import json
import tempfile
from pathlib import Path
from datetime import datetime


class ServerManager:
    """Manages the test server lifecycle."""
    
    def __init__(self, port=5555):
        self.port = port
        self.process = None
        self.server_url = f"http://localhost:{port}"
        self.log_dir = None
    
    def start(self):
        """Start the server in the background."""
        print(f"🚀 Starting server on port {self.port}...")
        
        # Create temp directory for logs
        self.log_dir = tempfile.mkdtemp(prefix="grab_integration_test_")
        print(f"📁 Logs will be written to: {self.log_dir}")
        
        # Create log files for server
        server_stdout = open(os.path.join(self.log_dir, "server_stdout.log"), "w")
        server_stderr = open(os.path.join(self.log_dir, "server_stderr.log"), "w")
        
        # Start the server with custom port using python -c
        server_code = f"""
import sys
import os
sys.path.insert(0, os.getcwd())
from src.grab.app import create_app
app, socketio = create_app()
socketio.run(app, debug=False, host='127.0.0.1', port={self.port}, allow_unsafe_werkzeug=True)
"""
        
        self.process = subprocess.Popen(
            [sys.executable, "-c", server_code],
            stdout=server_stdout,
            stderr=server_stderr,
            text=True,
            cwd=os.getcwd()
        )
        
        # Wait for server to be ready by checking API endpoint instead of root
        for i in range(30):  # 30 second timeout
            try:
                # Try to ping the API health endpoint - any API endpoint without auth should work
                response = requests.get(f"{self.server_url}/api/games", timeout=1)
                # Even if it returns 401 (unauthorized), that means the server is running
                if response.status_code in [200, 401, 403]:
                    print(f"✅ Server started successfully on {self.server_url}")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        
        print("❌ Server failed to start within 30 seconds")
        print(f"📋 Check server logs in: {self.log_dir}")
        self.stop()
        return False
    
    def stop(self):
        """Stop the server with escalating force."""
        if self.process:
            print("🛑 Stopping server...")
            try:
                # First try graceful termination
                self.process.terminate()
                self.process.wait(timeout=5)
                print("✅ Server stopped gracefully")
            except subprocess.TimeoutExpired:
                print("⚠️ Server didn't stop gracefully, sending SIGKILL...")
                try:
                    self.process.kill()
                    self.process.wait(timeout=5)
                    print("✅ Server force-killed")
                except subprocess.TimeoutExpired:
                    print("❌ Warning: Server process may still be running")
                except Exception as e:
                    print(f"❌ Warning: Error killing server: {e}")
            except Exception as e:
                print(f"❌ Warning: Error terminating server: {e}")
            finally:
                self.process = None
        
        if self.log_dir:
            print(f"📋 Server logs saved in: {self.log_dir}")
    
    def __enter__(self):
        if self.start():
            return self
        raise RuntimeError("Failed to start server")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class ClientTestRunner:
    """Runs client processes for testing."""
    
    def __init__(self, server_url, log_dir):
        self.server_url = server_url
        self.log_dir = log_dir
        self.client_script = Path("scripts/socketio_client.py")
        if not self.client_script.exists():
            raise FileNotFoundError(f"Client script not found: {self.client_script}")
    
    def run_client_commands(self, username, commands, timeout=15):
        """Run a client with a series of commands."""
        timestamp = datetime.now().strftime("%H%M%S")
        print(f"🤖 Running client '{username}' with commands: {commands}")
        
        # Create log files for this client
        stdout_file = os.path.join(self.log_dir, f"client_{username}_{timestamp}_stdout.log")
        stderr_file = os.path.join(self.log_dir, f"client_{username}_{timestamp}_stderr.log")
        input_file = os.path.join(self.log_dir, f"client_{username}_{timestamp}_input.log")
        
        # Prepare input
        input_text = username + "\n" + "\n".join(str(cmd) for cmd in commands if not isinstance(cmd, (int, float))) + "\n"
        
        # Save input to file for debugging
        with open(input_file, "w") as f:
            f.write(f"# Input for client '{username}' at {datetime.now()}\n")
            f.write(f"# Commands: {commands}\n")
            f.write(input_text)
        
        print(f"📁 Client '{username}' logs: {stdout_file}, {stderr_file}")
        
        try:
            with open(stdout_file, "w") as stdout_f, open(stderr_file, "w") as stderr_f:
                # Add header to log files
                stdout_f.write(f"# Client '{username}' stdout log - {datetime.now()}\n")
                stdout_f.write(f"# Server: {self.server_url}\n")
                stdout_f.write(f"# Commands: {commands}\n")
                stdout_f.write("# " + "="*50 + "\n\n")
                stdout_f.flush()
                
                stderr_f.write(f"# Client '{username}' stderr log - {datetime.now()}\n")
                stderr_f.write(f"# Server: {self.server_url}\n") 
                stderr_f.write(f"# Commands: {commands}\n")
                stderr_f.write("# " + "="*50 + "\n\n")
                stderr_f.flush()
                
                process = subprocess.Popen(
                    [sys.executable, str(self.client_script), self.server_url],
                    stdin=subprocess.PIPE,
                    stdout=stdout_f,
                    stderr=stderr_f,
                    text=True,
                    cwd=os.getcwd()
                )
                
                stdout_content, stderr_content = process.communicate(input=input_text, timeout=timeout)
            
            # Read the log files to get the content
            with open(stdout_file, "r") as f:
                stdout_content = f.read()
            with open(stderr_file, "r") as f:
                stderr_content = f.read()
            
            print(f"✅ Client '{username}' completed with return code: {process.returncode}")
            
            return {
                'returncode': process.returncode,
                'stdout': stdout_content,
                'stderr': stderr_content,
                'stdout_file': stdout_file,
                'stderr_file': stderr_file,
                'input_file': input_file
            }
            
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            
            # Read partial logs
            try:
                with open(stdout_file, "r") as f:
                    stdout_content = f.read()
                with open(stderr_file, "r") as f:
                    stderr_content = f.read()
            except:
                stdout_content = stderr_content = ""
            
            print(f"⏰ Client '{username}' timed out after {timeout}s")
            return {
                'returncode': -1,
                'stdout': stdout_content,
                'stderr': stderr_content,
                'timeout': True,
                'stdout_file': stdout_file,
                'stderr_file': stderr_file,
                'input_file': input_file
            }
        except Exception as e:
            print(f"❌ Client '{username}' failed: {e}")
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'error': e,
                'stdout_file': stdout_file if 'stdout_file' in locals() else None,
                'stderr_file': stderr_file if 'stderr_file' in locals() else None,
                'input_file': input_file if 'input_file' in locals() else None
            }
    
    def run_interleaved_clients(self, client_a, client_b, sequence, timeout=30):
        """Run two clients with interleaved commands to avoid race conditions."""
        timestamp = datetime.now().strftime("%H%M%S")
        
        # Create log files
        stdout_a = os.path.join(self.log_dir, f"client_{client_a}_{timestamp}_stdout.log")
        stderr_a = os.path.join(self.log_dir, f"client_{client_a}_{timestamp}_stderr.log") 
        stdout_b = os.path.join(self.log_dir, f"client_{client_b}_{timestamp}_stdout.log")
        stderr_b = os.path.join(self.log_dir, f"client_{client_b}_{timestamp}_stderr.log")
        
        print(f"📁 Interleaved clients logs: {stdout_a}, {stdout_b}")
        
        # Start both client processes
        try:
            with open(stdout_a, "w") as f_out_a, open(stderr_a, "w") as f_err_a, \
                 open(stdout_b, "w") as f_out_b, open(stderr_b, "w") as f_err_b:
                
                # Start client A
                proc_a = subprocess.Popen(
                    [sys.executable, str(self.client_script), self.server_url],
                    stdin=subprocess.PIPE,
                    stdout=f_out_a,
                    stderr=f_err_a,
                    text=True,
                    cwd=os.getcwd()
                )
                
                # Start client B 
                proc_b = subprocess.Popen(
                    [sys.executable, str(self.client_script), self.server_url],
                    stdin=subprocess.PIPE,
                    stdout=f_out_b,
                    stderr=f_err_b,
                    text=True,
                    cwd=os.getcwd()
                )
                
                # Send usernames first
                proc_a.stdin.write(client_a + "\n")
                proc_a.stdin.flush()
                proc_b.stdin.write(client_b + "\n") 
                proc_b.stdin.flush()
                
                time.sleep(2)  # Give time for login
                
                # Execute sequence
                for client, command in sequence:
                    print(f"📤 {client}: {command}")
                    if client == client_a:
                        proc_a.stdin.write(command + "\n")
                        proc_a.stdin.flush()
                    else:
                        proc_b.stdin.write(command + "\n")
                        proc_b.stdin.flush()
                    time.sleep(0.5)  # Small delay between commands
                
                # Close stdin and wait for completion
                proc_a.stdin.close()
                proc_b.stdin.close()
                
                try:
                    proc_a.wait(timeout=timeout)
                    proc_b.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    print(f"⏰ Client processes timed out after {timeout}s, cleaning up...")
                    self._cleanup_processes([proc_a, proc_b])
                    raise
            
            # Read the log files
            with open(stdout_a, "r") as f:
                stdout_content_a = f.read()
            with open(stderr_a, "r") as f:
                stderr_content_a = f.read()
            with open(stdout_b, "r") as f:
                stdout_content_b = f.read()
            with open(stderr_b, "r") as f:
                stderr_content_b = f.read()
            
            result_a = {
                'returncode': proc_a.returncode,
                'stdout': stdout_content_a,
                'stderr': stderr_content_a,
                'stdout_file': stdout_a,
                'stderr_file': stderr_a
            }
            
            result_b = {
                'returncode': proc_b.returncode,
                'stdout': stdout_content_b,
                'stderr': stderr_content_b,
                'stdout_file': stdout_b,
                'stderr_file': stderr_b
            }
            
            return result_a, result_b
            
        except Exception as e:
            print(f"❌ Interleaved client test failed: {e}")
            # Try to kill processes if they're still running
            self._cleanup_processes([proc_a, proc_b])
            raise
    
    def _cleanup_processes(self, processes):
        """Clean up client processes with escalating force."""
        for i, proc in enumerate(processes):
            if proc and proc.poll() is None:  # Process is still running
                client_name = f"client_{i+1}"
                print(f"🛑 Cleaning up {client_name}...")
                try:
                    # First try graceful termination
                    proc.terminate()
                    proc.wait(timeout=3)
                    print(f"✅ {client_name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    print(f"⚠️ {client_name} didn't stop gracefully, sending SIGKILL...")
                    try:
                        proc.kill()
                        proc.wait(timeout=3)
                        print(f"✅ {client_name} force-killed")
                    except subprocess.TimeoutExpired:
                        print(f"❌ Warning: {client_name} process may still be running (PID: {proc.pid})")
                    except Exception as e:
                        print(f"❌ Warning: Error killing {client_name}: {e}")
                except Exception as e:
                    print(f"❌ Warning: Error terminating {client_name}: {e}")


def print_client_summary(username, result):
    """Print a summary of client execution."""
    print(f"\n📊 Client '{username}' Summary:")
    print(f"   Return code: {result['returncode']}")
    if 'timeout' in result:
        print(f"   ⏰ TIMED OUT")
    if 'error' in result:
        print(f"   ❌ ERROR: {result['error']}")
    
    # Print key lines from stdout
    stdout_lines = result['stdout'].split('\n')
    important_lines = [line for line in stdout_lines if any(keyword in line for keyword in 
                      ['Successfully logged in', 'Game created', 'Joined game', 'Move successful', 
                       'Failed', 'Error', '✓', '✗', '❌'])]
    
    if important_lines:
        print("   Key output lines:")
        for line in important_lines[:5]:  # Show first 5 important lines
            print(f"     {line.strip()}")
    
    if result.get('stdout_file'):
        print(f"   📁 Full stdout: {result['stdout_file']}")
    if result.get('stderr_file'):
        print(f"   📁 Full stderr: {result['stderr_file']}")


def test_full_integration():
    """Test the full client-server integration."""
    print("🧪 Starting full client-server integration test")
    print("=" * 60)
    
    try:
        with ServerManager() as server:
            runner = ClientTestRunner(server.server_url, server.log_dir)
            
            # Test 1: Single client creates and lists games
            print("\n📋 TEST 1: Single client workflow")
            result1 = runner.run_client_commands(
                username="alice",
                commands=[
                    "create",
                    "list", 
                    "exit"
                ]
            )
            
            print_client_summary("alice", result1)
            
            if result1['returncode'] != 0:
                print("❌ TEST 1 FAILED - Non-zero return code")
                return False
            
            # Check for expected outputs
            if "Successfully logged in as alice" not in result1['stdout']:
                print("❌ TEST 1 FAILED: Login failed")
                return False
            
            if "Game created!" not in result1['stdout']:
                print("❌ TEST 1 FAILED: Game creation failed")
                return False
            
            print("✅ TEST 1 PASSED")
            
            # Test 2: Multi-client game flow with sequential command execution
            print("\n👥 TEST 2: Multi-client game flow")
            
            # Sequential list of (client, command) to avoid race conditions
            sequence = [
                ("bob", "create"),
                ("bob", "join 2"),      # Bob joins his own game
                ("charlie", "join 2"),  # Charlie joins bob's game  
                ("bob", "!start"),      # Bob starts the game
                ("bob", "cad"),         # Bob makes a move
                ("charlie", "cat"),     # Charlie makes a move
                ("bob", "!quit"),       # Bob leaves game mode
                ("charlie", "!quit"),   # Charlie leaves game mode
                ("bob", "exit"),        # Bob exits
                ("charlie", "exit")     # Charlie exits
            ]
            
            result_a, result_b = runner.run_interleaved_clients(
                client_a="bob",
                client_b="charlie", 
                sequence=sequence,
                timeout=30
            )
            
            print_client_summary("bob", result_a)
            print_client_summary("charlie", result_b)
            
            # Check results
            success = True
            
            # Check client A (bob)
            if result_a['returncode'] != 0:
                print("❌ TEST 2 FAILED: Client A failed")
                success = False
            elif "Successfully logged in as bob" not in result_a['stdout']:
                print("❌ TEST 2 FAILED: Client A login failed")
                success = False
            elif "Game created!" not in result_a['stdout']:
                print("❌ TEST 2 FAILED: Client A game creation failed")
                success = False
            elif "Joined game 2" not in result_a['stdout']:
                print("❌ TEST 2 FAILED: Client A failed to join own game")
                success = False
            elif "New letters drawn:" not in result_a['stdout']:
                print("❌ TEST 2 FAILED: Client A didn't receive letters drawn event")
                success = False
            
            # Check client B (charlie)
            if result_b['returncode'] != 0:
                print("❌ TEST 2 FAILED: Client B failed")
                success = False
            elif "Successfully logged in as charlie" not in result_b['stdout']:
                print("❌ TEST 2 FAILED: Client B login failed")
                success = False
            elif "Joined game 2" not in result_b['stdout']:
                print("❌ TEST 2 FAILED: Client B failed to join game")
                success = False
            elif "New letters drawn:" not in result_b['stdout']:
                print("❌ TEST 2 FAILED: Client B didn't receive letters drawn event")
                success = False
            
            if success:
                print("✅ TEST 2 PASSED")
            else:
                print("❌ TEST 2 FAILED")
                return False
            
            # Test 3: Error handling - try to join non-existent game
            print("\n🚫 TEST 3: Error handling")
            result3 = runner.run_client_commands(
                username="dave",
                commands=[
                    "join 999",  # Non-existent game
                    "exit"
                ]
            )
            
            print_client_summary("dave", result3)
            
            if result3['returncode'] != 0:
                print("❌ TEST 3 FAILED: Client failed unexpectedly")
                return False
            
            if "Game not found" not in result3['stdout'] and "Failed to join game" not in result3['stdout']:
                print("❌ TEST 3 FAILED: Expected error not found")
                return False
            
            print("✅ TEST 3 PASSED")
            
            print(f"\n🎉 ALL TESTS PASSED!")
            print(f"📁 All logs saved in: {server.log_dir}")
            return True
            
    except Exception as e:
        print(f"❌ Integration test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    print("🧪 Grab Game Client-Server Integration Test")
    print("=" * 60)
    print("This script tests the real client-server interaction")
    print("to catch issues that unit tests might miss.")
    print("All subprocess outputs are logged to temporary files.")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("run.py").exists():
        print("❌ Please run this script from the grab project root directory")
        sys.exit(1)
    
    if not Path("scripts/socketio_client.py").exists():
        print("❌ Client script not found at scripts/socketio_client.py")
        sys.exit(1)
    
    # Set up signal handler for clean shutdown
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}, cleaning up...")
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    success = test_full_integration()
    
    if success:
        print("\n🎉 Integration test completed successfully!")
        print("The client-server interaction is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Integration test failed!")
        print("There are issues with the client-server interaction.")
        print("Check the log files for detailed debugging information.")
        sys.exit(1)


if __name__ == "__main__":
    main()
