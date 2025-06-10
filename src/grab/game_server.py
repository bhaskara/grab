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
        pass


    def add_player(self, name : str):
        """Adds a new player.  Raises a RuntimeError if name already exists.

        """
        pass


    def list_players(self) -> List[str]:
        """Lists currently known players.

        """
        pass
        
    def list_games(self) -> List[str]:
        """Lists current game IDs.

        """
        pass

    def get_game_info(self, game_id : str) -> Tuple[str, List[str]]:
        """Given a game id, return the game status and players in the game.

        """
        pass

    def add_game(self) -> str:
        """Add a new game and return its ID.

        For now, IDs are consecutively increasing integers (converted to str).

        """
        pass

    def add_player_to_game(self, player : str, game_id : str):
        """Adds a given player to the game.

        Raise KeyError if player or game doesn't already exist.
        Raise RuntimeError if game is complete or if player is in another game.

        """
        pass

    def remove_game(self, game_id : str):
        """Remove the given game from the state.

        """
        pass

    def set_game_state(self, game_id : str, state : str):
        """Set the given game state.

        - Raises KeyError if game_id doesn't exist.
        - Raises ValueError if state isn't one of 'setup', 'running', 'paused',
          or 'done'.
          
        """
        pass

    
        

        
