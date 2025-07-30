"""Runnable driver script to test the server API.

First start the Flask server at some url.  Then, run this script using:
python api_driver.api SERVER_URL

When you run it, it will prompt you for a username and then connect to the server.

Once you enter it, you can choose between a few commands:
- start NEW_GAME_ID (starts new game)
- join GAME_ID (joins existing game)
- stop GAME_ID (stops running game)
- exit (exit script)

After each command other than exit or join, the script:
1) Prints a confirmation message upon success, or some representation of the HTTP error
2) Prints the current server status (games, players in each game, and game status)
3) Prompts you for the next command

After a join command, you go into a mode where you instead enter moves to be sent to the
server, after which the game state is printed.  This mode persists until the game ends.
Supported commands in gameplay mode:
- <word> - Attempt to make a word using available tiles
- status - Request current game status
- ready - Mark yourself as ready for next turn
- quit - Leave the game and return to main menu

"""

import sys
import json
import requests
import websocket
import threading
import time
from typing import Optional, Dict, Any


class GrabAPIClient:
    """Client for interacting with the Grab game server API."""
    
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self.session_token: Optional[str] = None
        self.player_id: Optional[str] = None
        self.username: Optional[str] = None
        self.ws: Optional[websocket.WebSocketApp] = None
        self.game_active = False
        self.current_game_id: Optional[str] = None
    
    def login(self, username: str) -> bool:
        """Login with username and store session token."""
        url = f"{self.server_url}/api/auth/login"
        data = {"username": username}
        
        try:
            response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
            result = response.json()
            
            if response.status_code == 200 and result.get('success'):
                self.session_token = result['data']['session_token']
                self.player_id = result['data']['player_id']
                self.username = username
                print(f"✓ Successfully logged in as {username}")
                return True
            else:
                print(f"✗ Login failed: {result.get('error', 'Unknown error')}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Connection error: {e}")
            return False
        except json.JSONDecodeError:
            print("✗ Invalid JSON response from server")
            return False
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers for authenticated requests."""
        return {
            'Authorization': f'Bearer {self.session_token}',
            'Content-Type': 'application/json'
        }
    
    def create_game(self) -> Optional[str]:
        """Create a new game and return the game ID."""
        url = f"{self.server_url}/api/games"
        
        try:
            response = requests.post(url, json={}, headers=self._get_auth_headers())
            result = response.json()
            
            if response.status_code == 201 and result.get('success'):
                game_id = result['data']['game_id']
                print(f"✓ Game created successfully! Game ID: {game_id}")
                return game_id
            else:
                print(f"✗ Failed to create game: {result.get('error', 'Unknown error')}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"✗ Connection error: {e}")
            return None
        except json.JSONDecodeError:
            print("✗ Invalid JSON response from server")
            return None
    
    def join_game(self, game_id: str) -> bool:
        """Join an existing game."""
        url = f"{self.server_url}/api/games/{game_id}/join"
        
        try:
            response = requests.post(url, headers=self._get_auth_headers())
            result = response.json()
            
            if response.status_code == 200 and result.get('success'):
                print(f"✓ Successfully joined game {game_id}")
                return True
            else:
                print(f"✗ Failed to join game: {result.get('error', 'Unknown error')}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Connection error: {e}")
            return False
        except json.JSONDecodeError:
            print("✗ Invalid JSON response from server")
            return False
    
    def stop_game(self, game_id: str) -> bool:
        """Stop a game."""
        url = f"{self.server_url}/api/games/{game_id}"
        
        try:
            response = requests.delete(url, headers=self._get_auth_headers())
            result = response.json()
            
            if response.status_code == 200 and result.get('success'):
                print(f"✓ Successfully stopped game {game_id}")
                return True
            else:
                print(f"✗ Failed to stop game: {result.get('error', 'Unknown error')}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Connection error: {e}")
            return False
        except json.JSONDecodeError:
            print("✗ Invalid JSON response from server")
            return False
    
    def start_game(self, game_id: str) -> bool:
        """Start a game."""
        url = f"{self.server_url}/api/games/{game_id}/start"
        
        try:
            response = requests.post(url, headers=self._get_auth_headers())
            result = response.json()
            
            if response.status_code == 200 and result.get('success'):
                print(f"✓ Successfully started game {game_id}")
                return True
            else:
                print(f"✗ Failed to start game: {result.get('error', 'Unknown error')}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Connection error: {e}")
            return False
        except json.JSONDecodeError:
            print("✗ Invalid JSON response from server")
            return False
    
    def get_all_games(self) -> Optional[Dict[str, Any]]:
        """Get information about all games on the server."""
        url = f"{self.server_url}/api/games"
        
        try:
            response = requests.get(url, headers=self._get_auth_headers())
            result = response.json()
            
            if response.status_code == 200 and result.get('success'):
                return result['data']
            else:
                print(f"✗ Failed to get games: {result.get('error', 'Unknown error')}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"✗ Connection error: {e}")
            return None
        except json.JSONDecodeError:
            print("✗ Invalid JSON response from server")
            return None
    
    def get_game_info(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific game."""
        url = f"{self.server_url}/api/games/{game_id}"
        
        try:
            response = requests.get(url, headers=self._get_auth_headers())
            result = response.json()
            
            if response.status_code == 200 and result.get('success'):
                return result['data']
            else:
                return None
        except (requests.exceptions.RequestException, json.JSONDecodeError):
            return None
    
    def display_server_status(self):
        """Display current server status - games and their players."""
        print("\n" + "="*50)
        print("SERVER STATUS")
        print("="*50)
        
        games_data = self.get_all_games()
        if not games_data or not games_data['games']:
            print("No games on server")
            print("="*50)
            return
        
        for game_info in games_data['games']:
            game_id = game_info['game_id']
            print(f"\nGame {game_id}:")
            print(f"  Status: {game_info['status']}")
            print(f"  Max Players: {game_info['max_players']}")
            print(f"  Current Players: {len(game_info['current_players'])}")
            if game_info['current_players']:
                for player in game_info['current_players']:
                    print(f"    - {player['username']} (joined: {player['joined_at']})")
            else:
                print("    - No players")
            print(f"  Created: {game_info['created_at']}")
            if game_info['started_at']:
                print(f"  Started: {game_info['started_at']}")
            if game_info['finished_at']:
                print(f"  Finished: {game_info['finished_at']}")
        
        print(f"\nTotal games: {games_data['total_games']}")
        print("="*50)
    
    def display_game_state(self, game_state: Dict[str, Any]):
        """Display the current game state in a readable format."""
        print("\n" + "="*60)
        print(f"GAME STATE - {game_state.get('game_id', 'Unknown')}")
        print("="*60)
        
        # Game info
        print(f"Status: {game_state.get('status', 'unknown')}")
        print(f"Turn: {game_state.get('current_turn', 0)}")
        time_remaining = game_state.get('turn_time_remaining')
        if time_remaining is not None:
            print(f"Time remaining: {time_remaining // 1000}s")
        
        # Players and scores
        print("\nPlayers:")
        players = game_state.get('players', {})
        for username, player_info in players.items():
            status_indicators = []
            if player_info.get('connected', False):
                status_indicators.append("online")
            else:
                status_indicators.append("offline")
            if player_info.get('ready_for_next_turn', False):
                status_indicators.append("ready")
            
            status_str = f" ({', '.join(status_indicators)})" if status_indicators else ""
            print(f"  {username}: {player_info.get('score', 0)} points{status_str}")
        
        # Game-specific state (pretty-printed JSON)
        state_json = game_state.get('state', '{}')
        try:
            game_specific_state = json.loads(state_json)
            print("\nGame State:")
            print(json.dumps(game_specific_state, indent=2))
        except json.JSONDecodeError:
            print(f"\nGame state data: {state_json}")
        
        print("="*60)
    
    def on_websocket_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'game_state':
                self.display_game_state(data['data'])
            elif msg_type == 'move_result':
                if data.get('success'):
                    print("✓ Move successful!")
                    if 'game_state' in data:
                        self.display_game_state(data['game_state'])
                else:
                    print(f"✗ Move failed: {data.get('error', 'Unknown error')}")
            elif msg_type == 'turn_ended':
                reason = data.get('reason', 'unknown')
                next_turn_delay = data.get('next_turn_starts_in', 0) // 1000
                print(f"\n🔄 Turn ended ({reason}). Next turn starts in {next_turn_delay}s...")
            elif msg_type == 'game_ended':
                reason = data.get('reason', 'unknown')
                winner = data.get('winner')
                print(f"\n🏁 Game ended ({reason})")
                if winner:
                    print(f"Winner: {winner}")
                
                final_scores = data.get('final_scores', {})
                if final_scores:
                    print("Final scores:")
                    for username, score in final_scores.items():
                        print(f"  {username}: {score} points")
                
                self.game_active = False
                print("\nReturning to main menu...")
            elif msg_type == 'player_disconnected':
                player = data.get('player', 'Unknown')
                print(f"📴 {player} disconnected")
            elif msg_type == 'player_reconnected':
                player = data.get('player', 'Unknown')
                print(f"📱 {player} reconnected")
            elif msg_type == 'error':
                print(f"❌ Game error: {data.get('message', 'Unknown error')}")
            else:
                print(f"Unknown message type: {msg_type}")
                print(f"Data: {data}")
                
        except json.JSONDecodeError:
            print(f"Invalid JSON message: {message}")
    
    def on_websocket_error(self, ws, error):
        """Handle WebSocket errors."""
        print(f"❌ WebSocket error: {error}")
        self.game_active = False
    
    def on_websocket_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close."""
        if self.game_active:
            print("🔌 WebSocket connection closed")
            self.game_active = False
    
    def on_websocket_open(self, ws):
        """Handle WebSocket connection open."""
        print("✓ Connected to game!")
        # Request initial game status
        self.send_websocket_message({"type": "get_status"})
    
    def send_websocket_message(self, message: Dict[str, Any]):
        """Send a message via WebSocket."""
        self.ws.send(json.dumps(message))
    
    def connect_to_game(self, game_id: str) -> bool:
        """Establish WebSocket connection to a game."""
        # Convert HTTP/HTTPS URL to WebSocket URL
        ws_url = self.server_url.replace('http://', 'ws://').replace('https://', 'wss://')
        connect_url = f"{ws_url}/api/games/{game_id}/connect"
        
        headers = [f"Authorization: Bearer {self.session_token}"]
        
        try:
            self.ws = websocket.WebSocketApp(
                connect_url,
                header=headers,
                on_message=self.on_websocket_message,
                on_error=self.on_websocket_error,
                on_close=self.on_websocket_close,
                on_open=self.on_websocket_open
            )
            
            self.current_game_id = game_id
            self.game_active = True
            
            # Run WebSocket in a separate thread
            wst = threading.Thread(target=self.ws.run_forever)
            wst.daemon = True
            wst.start()
            
            # Give connection time to establish
            time.sleep(1)
            return self.game_active
            
        except Exception as e:
            print(f"❌ Failed to connect to game: {e}")
            return False
    
    def disconnect_from_game(self):
        """Disconnect from the current game."""
        if self.ws:
            self.game_active = False
            self.ws.close()
            self.ws = None
            self.current_game_id = None
    
    def play_game_mode(self, game_id: str):
        """Enter interactive game play mode."""
        print(f"\n🎮 Entering game mode for {game_id}")
        print("Commands: <word> to make a move, 'status' for current state, 'ready' when done with turn, 'quit' to leave")
        
        if not self.connect_to_game(game_id):
            print("Failed to connect to game WebSocket")
            return
        
        try:
            while self.game_active:
                command = input("\nGame> ").strip()
                
                if not command:
                    continue
                
                if command.lower() == 'quit':
                    break
                elif command.lower() == 'status':
                    self.send_websocket_message({"type": "get_status"})
                elif command.lower() == 'ready':
                    self.send_websocket_message({
                        "type": "player_action", 
                        "data": "ready_for_next_turn"
                    })
                    print("✓ Marked as ready for next turn")
                else:
                    # Treat as a word move
                    self.send_websocket_message({
                        "type": "move",
                        "data": command.upper()
                    })
                    print(f"🎯 Attempting to make word: {command.upper()}")
        
        except KeyboardInterrupt:
            print("\n⏹️  Game interrupted")
        finally:
            self.disconnect_from_game()
            print("📴 Disconnected from game")


def main():
    """Main driver function."""
    if len(sys.argv) != 2:
        print("Usage: python api_driver.py SERVER_URL")
        print("Example: python api_driver.py http://localhost:5000")
        sys.exit(1)
    
    server_url = sys.argv[1]
    client = GrabAPIClient(server_url)
    
    # Login
    print(f"Connecting to server at {server_url}")
    username = input("Enter your username: ").strip()
    if not username:
        print("Username cannot be empty")
        sys.exit(1)
    
    if not client.login(username):
        print("Failed to login. Exiting.")
        sys.exit(1)
    
    # Add after login success:
    print("⚠️  Note: This script requires Socket.IO for real-time gameplay.")
    print("Use socketio_client.py for full functionality, or ensure WebSocket connection is established.")
    
    print("\nAvailable commands:")
    print("  start - Create a new game")
    print("  start_game <game_id> - Start an existing game")
    print("  join <game_id> - Join an existing game")
    print("  stop <game_id> - Stop a game")
    print("  exit - Exit the program")
    print("\nNote: After creating a game, you need to join it before starting it.")
    
    # Main command loop
    while True:
        print("\n" + "-"*30)
        command = input("Enter command: ").strip()
        
        if not command:
            continue
        
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == "exit":
            print("Goodbye!")
            break
        elif cmd == "start":
            game_id = client.create_game()
            if game_id:
                client.display_server_status()
        elif cmd == "start_game":
            if len(parts) != 2:
                print("Usage: start_game <game_id>")
                continue
            game_id = parts[1]
            if client.start_game(game_id):
                client.display_server_status()
        elif cmd == "join":
            if len(parts) != 2:
                print("Usage: join <game_id>")
                continue
            game_id = parts[1]
            if client.join_game(game_id):
                client.display_server_status()
                # Enter game mode after successful join
                client.play_game_mode(game_id)
        elif cmd == "stop":
            if len(parts) != 2:
                print("Usage: stop <game_id>")
                continue
            game_id = parts[1]
            if client.stop_game(game_id):
                client.display_server_status()
        else:
            print("Unknown command. Available commands: start, start_game <game_id>, join <game_id>, stop <game_id>, exit")


if __name__ == "__main__":
    main()
