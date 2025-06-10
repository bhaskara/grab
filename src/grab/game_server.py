from typing import List, Tuple

class GameServer(object):
    """Represents the game server state.

    The model here is:
    - There is a set of known players, with string names.
    - There is a set of games, each with a unique string ID.
    - Each game is in one of four states: 'setup', 'running', 'paused', or
      'done'.
    - Each player is currently participating in at most one game.

    """
    def __init__(self):
        """Initialize the GameServer with empty state."""
        self.players = set()  # Set of player names
        self.games = {}  # game_id -> {'state': str, 'players': list}
        self.next_game_id = 1  # Counter for consecutive game IDs
        self.player_to_game = {}  # player_name -> game_id mapping


    def add_player(self, name : str):
        """Adds a new player.  Raises a RuntimeError if name already exists.

        """
        if name in self.players:
            raise RuntimeError(f"Player '{name}' already exists")
        self.players.add(name)


    def list_players(self) -> List[str]:
        """Lists currently known players.

        """
        return list(self.players)
        
    def list_games(self) -> List[str]:
        """Lists current game IDs.

        """
        return list(self.games.keys())

    def get_game_info(self, game_id : str) -> Tuple[str, List[str]]:
        """Given a game id, return the game status and players in the game.

        """
        if game_id not in self.games:
            raise KeyError(f"Game '{game_id}' does not exist")
        
        game = self.games[game_id]
        return game['state'], game['players'].copy()

    def add_game(self) -> str:
        """Add a new game and return its ID.

        For now, IDs are consecutively increasing integers (converted to str).

        """
        game_id = str(self.next_game_id)
        self.next_game_id += 1
        
        self.games[game_id] = {
            'state': 'setup',
            'players': []
        }
        
        return game_id

    def add_player_to_game(self, player : str, game_id : str):
        """Adds a given player to the game.

        Raise KeyError if player or game doesn't already exist.
        Raise RuntimeError if game is complete or if player is in another game.

        """
        if player not in self.players:
            raise KeyError(f"Player '{player}' does not exist")
        
        if game_id not in self.games:
            raise KeyError(f"Game '{game_id}' does not exist")
        
        # Check if game is complete
        if self.games[game_id]['state'] == 'done':
            raise RuntimeError(f"Game '{game_id}' is complete")
        
        # Check if player is already in another game
        if player in self.player_to_game:
            raise RuntimeError(f"Player '{player}' is already in another game")
        
        # Add player to game
        self.games[game_id]['players'].append(player)
        self.player_to_game[player] = game_id

    def remove_game(self, game_id : str):
        """Remove the given game from the state.

        """
        if game_id in self.games:
            # Free up players from this game
            players_in_game = self.games[game_id]['players']
            for player in players_in_game:
                if player in self.player_to_game:
                    del self.player_to_game[player]
            
            # Remove the game
            del self.games[game_id]

    def set_game_state(self, game_id : str, state : str):
        """Set the given game state.

        - Raises KeyError if game_id doesn't exist.
        - Raises ValueError if state isn't one of 'setup', 'running', 'paused',
          or 'done'.
          
        """
        if game_id not in self.games:
            raise KeyError(f"Game '{game_id}' does not exist")
        
        valid_states = {'setup', 'running', 'paused', 'done'}
        if state not in valid_states:
            raise ValueError(f"Invalid state '{state}'. Must be one of: {valid_states}")
        
        self.games[game_id]['state'] = state
