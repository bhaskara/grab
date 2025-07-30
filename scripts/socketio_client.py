#!/usr/bin/env python3
"""
Socket.IO compatible console client for the Grab game server.

This client connects to the Flask-SocketIO server and allows interactive gameplay
from the command line.

Usage:
    python socketio_client.py http://localhost:5000

Commands after login:
    create - Create a new game
    join <game_id> - Join an existing game  
    start <game_id> - Start a game (creator only)
    list - List all games
    exit - Exit the program

In game mode:
    <word> - Attempt to make a word
    !ready or !r - Mark ready for next turn
    !print or !p - Get current game status
    !end or !e - End the game (creator only)
    !quit or !q - Leave game and return to main menu
"""

import sys
import json
import requests
import socketio
import threading
import time
import queue
import select
from typing import Optional, Dict, Any


class GrabSocketIOClient:
    """Socket.IO client for the Grab game server."""
    
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self.session_token: Optional[str] = None
        self.username: Optional[str] = None
        self.sio = socketio.Client()
        self.game_active = False
        self.current_game_id: Optional[str] = None
        self.input_queue = queue.Queue()
        self.input_thread = None
        self.should_refresh_prompt = False
        self.current_prompt = ""
        self.setup_socketio_handlers()
    
    def setup_socketio_handlers(self):
        """Set up Socket.IO event handlers."""
        
        @self.sio.on('connected')
        def on_connected(data):
            print(f"✓ Connected to server: {data.get('message', '')}")
            if 'game_state' in data:
                self.display_game_state(data['game_state']['data'])
        
        @self.sio.on('game_state')
        def on_game_state(data):
            self.display_game_state(data['data'])
            self._refresh_prompt()
        
        @self.sio.on('move_result')
        def on_move_result(data):
            if data.get('success'):
                print("✓ Move successful!")
                if 'game_state' in data:
                    self.display_game_state(data['game_state'])
            else:
                print(f"✗ Move failed: {data.get('error', 'Unknown error')}")
            self._refresh_prompt()
        
        @self.sio.on('player_disconnected')
        def on_player_disconnected(data):
            player = data.get('player', 'Unknown')
            print(f"📴 {player} disconnected")
            self._refresh_prompt()
        
        @self.sio.on('player_reconnected')
        def on_player_reconnected(data):
            player = data.get('player', 'Unknown')
            print(f"📱 {player} reconnected")
            self._refresh_prompt()
        
        @self.sio.on('letters_drawn')
        def on_letters_drawn(data):
            event_data = data.get('data', {})
            letters_drawn = event_data.get('letters_drawn', [])
            letters_remaining = event_data.get('letters_remaining_in_bag', 0)
            
            print(f"\n🎯 New letters drawn: {', '.join(letters_drawn)}")
            print(f"💼 Letters remaining in bag: {letters_remaining}")
            
            # Also display updated game state if provided
            if 'game_state' in event_data:
                self.display_game_state(event_data['game_state'])
            self._refresh_prompt()

        @self.sio.on('error')
        def on_error(data):
            print(f"❌ Server error: {data.get('message', 'Unknown error')}")
            self._refresh_prompt()
        
        @self.sio.on('connect')
        def on_connect():
            print("🔌 Socket.IO connected")
        
        @self.sio.on('disconnect')
        def on_disconnect():
            if self.game_active:
                print("🔌 Socket.IO disconnected")
                self.game_active = False
    
    def _refresh_prompt(self):
        """Signal that the prompt should be refreshed after output."""
        self.should_refresh_prompt = True
    
    def _input_thread_func(self):
        """Thread function to handle non-blocking input."""
        while self.game_active and self.sio.connected:
            try:
                # Simple blocking input in thread
                line = input()
                if line and self.game_active:
                    self.input_queue.put(line.strip())
            except (EOFError, KeyboardInterrupt):
                break
            except Exception:
                time.sleep(0.1)
    
    def _get_input_non_blocking(self, prompt: str) -> Optional[str]:
        """Get input without blocking, allowing Socket.IO events to be processed."""
        self.current_prompt = prompt
        
        # Start input thread if not running
        if self.input_thread is None or not self.input_thread.is_alive():
            self.input_thread = threading.Thread(target=self._input_thread_func, daemon=True)
            self.input_thread.start()
            # Small delay to let the thread get ready
            time.sleep(0.05)
        
        # Show prompt initially if not already shown
        if not hasattr(self, '_prompt_shown') or not self._prompt_shown:
            print(prompt, end='', flush=True)
            self._prompt_shown = True
        
        while self.game_active and self.sio.connected:
            try:
                # Check for input with a timeout
                result = self.input_queue.get(timeout=0.1)
                self._prompt_shown = False  # Reset for next time
                return result
            except queue.Empty:
                # Check if we need to refresh the prompt
                if self.should_refresh_prompt:
                    self.should_refresh_prompt = False
                    print(f"\n{prompt}", end='', flush=True)
                    self._prompt_shown = True
                continue
        
        return None
    
    def login(self, username: str) -> bool:
        """Login with username and store session token."""
        url = f"{self.server_url}/api/auth/login"
        data = {"username": username}
        
        try:
            response = requests.post(url, json=data)
            result = response.json()
            
            if response.status_code == 200 and result.get('success'):
                self.session_token = result['data']['session_token']
                self.username = username
                print(f"✓ Successfully logged in as {username}")
                return True
            else:
                print(f"✗ Login failed: {result.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            print(f"✗ Login error: {e}")
            return False
    
    def connect_socketio(self) -> bool:
        """Connect to the Socket.IO server."""
        try:
            self.sio.connect(self.server_url, auth={'token': self.session_token})
            return True
        except Exception as e:
            print(f"✗ Socket.IO connection failed: {e}")
            return False
    
    def disconnect_socketio(self):
        """Disconnect from Socket.IO server."""
        if self.sio.connected:
            self.sio.disconnect()
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers for HTTP requests."""
        return {
            'Authorization': f'Bearer {self.session_token}',
            'Content-Type': 'application/json'
        }
    
    def create_game(self, test_letters=None) -> Optional[str]:
        """Create a new game.
        
        Parameters
        ----------
        test_letters : list of str, optional
            For testing: specific letters to place in the pool (e.g., ['a', 'b', 'c', 'd', 'e'])
        """
        url = f"{self.server_url}/api/games"
        
        # Prepare request data
        data = {}
        if test_letters:
            data['test_letters'] = test_letters
        
        try:
            response = requests.post(url, json=data, headers=self._get_auth_headers())
            result = response.json()
            
            if response.status_code == 201 and result.get('success'):
                game_id = result['data']['game_id']
                if test_letters:
                    print(f"✓ Test game created with letters {test_letters}! Game ID: {game_id}")
                else:
                    print(f"✓ Game created! Game ID: {game_id}")
                return game_id
            else:
                print(f"✗ Failed to create game: {result.get('error', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"✗ Create game error: {e}")
            return None
    
    def join_game(self, game_id: str) -> bool:
        """Join an existing game."""
        url = f"{self.server_url}/api/games/{game_id}/join"
        
        try:
            # Send empty JSON data to satisfy API requirements
            response = requests.post(url, json={}, headers=self._get_auth_headers())
            
            # Check if response contains JSON
            if response.headers.get('content-type', '').startswith('application/json'):
                result = response.json()
            else:
                # Handle non-JSON response (likely an error)
                print(f"✗ Server returned non-JSON response: {response.text}")
                return False
            
            if response.status_code == 200 and result.get('success'):
                print(f"✓ Joined game {game_id}")
                return True
            else:
                print(f"✗ Failed to join game: {result.get('error', 'Unknown error')}")
                return False
        except requests.exceptions.JSONDecodeError as e:
            print(f"✗ Join game error - invalid JSON response: {e}")
            print(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return False
        except Exception as e:
            print(f"✗ Join game error: {e}")
            return False
    
    def start_game(self, game_id: str) -> bool:
        """Start a game."""
        url = f"{self.server_url}/api/games/{game_id}/start"
        
        try:
            response = requests.post(url, headers=self._get_auth_headers())
            result = response.json()
            
            if response.status_code == 200 and result.get('success'):
                print(f"✓ Started game {game_id}")
                return True
            else:
                print(f"✗ Failed to start game: {result.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            print(f"✗ Start game error: {e}")
            return False
    
    def end_game(self, game_id: str) -> bool:
        """End/stop a game.
        
        Parameters
        ----------
        game_id : str
            The ID of the game to end
            
        Returns
        -------
        bool
            True if the game was successfully ended, False otherwise
        """
        url = f"{self.server_url}/api/games/{game_id}"
        
        try:
            response = requests.delete(url, headers=self._get_auth_headers())
            
            # Check if response contains JSON
            if response.headers.get('content-type', '').startswith('application/json'):
                result = response.json()
            else:
                # Handle non-JSON response (likely an error)
                print(f"✗ Server returned non-JSON response: {response.text}")
                return False
            
            if response.status_code == 200 and result.get('success'):
                print(f"✓ Ended game {game_id}")
                return True
            else:
                print(f"✗ Failed to end game: {result.get('error', 'Unknown error')}")
                return False
        except requests.exceptions.JSONDecodeError as e:
            print(f"✗ End game error - invalid JSON response: {e}")
            print(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return False
        except Exception as e:
            print(f"✗ End game error: {e}")
            return False
    
    def list_games(self):
        """List all games on the server."""
        url = f"{self.server_url}/api/games"
        
        try:
            response = requests.get(url, headers=self._get_auth_headers())
            result = response.json()
            
            if response.status_code == 200 and result.get('success'):
                games = result['data']['games']
                if not games:
                    print("No games on server")
                    return
                
                print("\n" + "="*50)
                print("GAMES ON SERVER")
                print("="*50)
                
                for game in games:
                    print(f"\nGame {game['game_id']}:")
                    print(f"  Status: {game['status']}")
                    print(f"  Players: {len(game['current_players'])}/{game['max_players']}")
                    for player in game['current_players']:
                        print(f"    - {player['username']}")
                    print(f"  Created: {game['created_at']}")
                    if game.get('started_at'):
                        print(f"  Started: {game['started_at']}")
                
                print("="*50)
            else:
                print(f"✗ Failed to list games: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"✗ List games error: {e}")
    
    def display_game_state(self, game_state: Dict[str, Any]):
        """Display current game state."""
        print("\n" + "="*60)
        print(f"GAME STATE - {game_state.get('game_id', 'Unknown')}")
        print("="*60)
        
        print(f"Status: {game_state.get('status', 'unknown')}")
        print(f"Turn: {game_state.get('current_turn', 0)}")
        print(f"Game Type: {game_state.get('game_type', 'unknown')}")
        
        # Players and scores
        players = game_state.get('players', {})
        if players:
            print("\nPlayers:")
            for username, player_info in players.items():
                status = "online" if player_info.get('connected') else "offline"
                ready = " (ready)" if player_info.get('ready_for_next_turn') else ""
                print(f"  {username}: {player_info.get('score', 0)} points ({status}){ready}")
        
        # Game-specific state
        state_json = game_state.get('state', '{}')
        try:
            state_data = json.loads(state_json)
            if state_data:
                print("\nGame State:")
                if game_state.get('game_type') == 'grab':
                    # Format Grab game state nicely
                    if 'pool' in state_data:
                        pool_letters = self._format_letter_array(state_data['pool'])
                        print(f"  Pool: {pool_letters}")
                    
                    if 'words_per_player' in state_data:
                        print("  Player Words:")
                        for i, words in enumerate(state_data['words_per_player']):
                            if words:
                                print(f"    Player {i}: {', '.join(words)}")
                            else:
                                print(f"    Player {i}: (no words)")
                    
                    if 'bag' in state_data:
                        bag_count = sum(state_data['bag'])
                        print(f"  Letters remaining in bag: {bag_count}")
                else:
                    # For dummy games or others, show raw JSON
                    print(json.dumps(state_data, indent=2))
        except json.JSONDecodeError:
            print(f"Raw state: {state_json}")
        
        print("="*60)
    
    def _format_letter_array(self, letter_array):
        """Convert letter count array to readable string."""
        letters = []
        for i, count in enumerate(letter_array):
            if count > 0:
                letter = chr(ord('a') + i)
                letters.extend([letter] * count)
        return ' '.join(letters) if letters else "(empty)"
    
    def enter_game_mode(self, game_id: str):
        """Enter interactive game mode."""
        print(f"\n🎮 Entering game mode for {game_id}")
        print("Commands: <word> to make a move, !ready/!r for next turn, !print/!p for state, !start/!s to start game, !end/!e to end game, !quit/!q to leave")
        
        self.current_game_id = game_id
        self.game_active = True
        
        # Request initial game status
        self.sio.emit('get_status')
        
        try:
            while self.game_active and self.sio.connected:
                command = self._get_input_non_blocking("Game> ")
                
                if command is None:
                    continue
                
                if not command:
                    continue
                
                # Handle commands starting with !
                if command.startswith('!'):
                    action = command[1:].lower()
                    
                    if action in ['quit', 'q']:
                        print("📴 Leaving game...")
                        break
                    elif action in ['print', 'p']:
                        self.sio.emit('get_status')
                    elif action in ['ready', 'r']:
                        self.sio.emit('player_action', {'data': 'ready_for_next_turn'})
                        print("✓ Marked as ready for next turn")
                    elif action in ['start', 's']:
                        if self.start_game(self.current_game_id):
                            print("✓ Game started!")
                        else:
                            print("✗ Failed to start game (you may not be the creator)")
                    elif action in ['end', 'e']:
                        if self.end_game(self.current_game_id):
                            print("✓ Game ended!")
                            # Request final game state
                            self.sio.emit('get_status')
                        else:
                            print("✗ Failed to end game (you may not be the creator)")
                    else:
                        print(f"Unknown action: !{action}")
                        print("Available actions: !ready/!r, !print/!p, !start/!s, !end/!e, !quit/!q")
                else:
                    # Treat as a word move
                    self.sio.emit('move', {'data': command.lower()})
                    print(f"🎯 Attempting to make word: {command.lower()}")
        
        except KeyboardInterrupt:
            print("\n⏹️  Game interrupted")
        finally:
            self.game_active = False
            self.current_game_id = None
            print("📴 Left game mode")


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python socketio_client.py SERVER_URL")
        print("Example: python socketio_client.py http://localhost:5000")
        sys.exit(1)
    
    server_url = sys.argv[1]
    client = GrabSocketIOClient(server_url)
    
    # Login
    print(f"Connecting to server at {server_url}")
    username = input("Enter your username: ").strip()
    if not username:
        print("Username cannot be empty")
        sys.exit(1)
    
    if not client.login(username):
        sys.exit(1)
    
    # Connect Socket.IO
    if not client.connect_socketio():
        sys.exit(1)
    
    print("\nAvailable commands:")
    print("  create - Create a new game")
    print("  join <game_id> - Join a game")
    print("  start <game_id> - Start a game (creator only)")
    print("  list - List all games")
    print("  exit - Exit the program")
    
    try:
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
            elif cmd == "create":
                game_id = client.create_game()
                if game_id:
                    print(f"Created game {game_id}. Use 'join {game_id}' to join it.")
            elif cmd == "join":
                if len(parts) != 2:
                    print("Usage: join <game_id>")
                    continue
                game_id = parts[1]
                if client.join_game(game_id):
                    # Enter game mode after successful join
                    client.enter_game_mode(game_id)
            elif cmd == "start":
                if len(parts) != 2:
                    print("Usage: start <game_id>")
                    continue
                game_id = parts[1]
                client.start_game(game_id)
            elif cmd == "list":
                client.list_games()
            else:
                print("Unknown command. Available: create, join <game_id>, start <game_id>, list, exit")
    
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
    finally:
        client.disconnect_socketio()


if __name__ == "__main__":
    main()