"""Runnable driver script to test the server API.

First start the Flask server at some url.  Then, run this script using:
python api_driver.api SERVER_URL

When you run it, it will prompt you for a username and then connect to the server.

Once you enter it, you can choose between a few commands:
- start NEW_GAME_ID (starts new game)
- join GAME_ID (joins existing game)
- leave GAME_ID (leaves previously joined game)
- exit (exit script)

After each command other than exit, the script:
1) Prints a confirmation message upon success, or some representation of the HTTP error
2) Prints the current server status (games, players in each game, and game status)
3) Prompts you for the next command

"""

import sys
import json
import requests
from typing import Optional, Dict, Any


class GrabAPIClient:
    """Client for interacting with the Grab game server API."""
    
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self.session_token: Optional[str] = None
        self.player_id: Optional[str] = None
        self.username: Optional[str] = None
        self.active_games: Dict[str, Dict[str, Any]] = {}
    
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
                self.active_games[game_id] = result['data']
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
    
    def leave_game(self, game_id: str) -> bool:
        """Leave a game."""
        url = f"{self.server_url}/api/games/{game_id}/leave"
        
        try:
            response = requests.delete(url, headers=self._get_auth_headers())
            result = response.json()
            
            if response.status_code == 200 and result.get('success'):
                print(f"✓ Successfully left game {game_id}")
                return True
            else:
                print(f"✗ Failed to leave game: {result.get('error', 'Unknown error')}")
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
        
        if not self.active_games:
            print("No active games")
            return
        
        for game_id in list(self.active_games.keys()):
            game_info = self.get_game_info(game_id)
            if game_info:
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
            else:
                print(f"\nGame {game_id}: (Unable to fetch info)")
        
        print("="*50)


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
    
    print("\nAvailable commands:")
    print("  start - Create a new game")
    print("  start_game <game_id> - Start an existing game")
    print("  join <game_id> - Join an existing game")
    print("  leave <game_id> - Leave a game")
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
                client.active_games[game_id] = {}  # Track this game
                client.display_server_status()
        elif cmd == "leave":
            if len(parts) != 2:
                print("Usage: leave <game_id>")
                continue
            game_id = parts[1]
            if client.leave_game(game_id):
                client.active_games.pop(game_id, None)  # Stop tracking this game
                client.display_server_status()
        else:
            print("Unknown command. Available commands: start, start_game <game_id>, join <game_id>, leave <game_id>, exit")


if __name__ == "__main__":
    main()
