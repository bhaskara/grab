from typing import List, Tuple

class DummyGrab(object):
    """This is a very simple dummy game that will be used instead of the real
    grab game when testing the server functionality.

    The way the game works is as follows:
    - The game is divided into rounds.
    - The game object keeps track of which round it is, and whether the game
      is finished.
    - On each round, each player can make multiple moves, each of which is
      an arbitrary english word.
    - The players can move in any order during a round, and each player can
      make multiple moves.
    - If a player plays a word, that word must be longer than any word
      previously played by that player in the round.
    - A player signifies they're done with the round by sending the empty
      string.
    - When all players are done with the round, the round ends, and a summary
      is created containing each player's name and the final word they sent.
      For example, if during round 3, Alice plays "cat", Bob plays "horse", and
      Alice plays "duck", then the summary is "On round 3, Alice played duck and
      Bob played horse".
    - The game finishes when there's a round where no player sends any words.
    - The game maintains the summaries for the past three rounds, and this is
      known as the current history.

    """
    def __init__(self, players : List[str]):
        """Initialize the DummyGrab game with given players."""
        self.players = set(players)
        self.current_round = 1
        self.is_running = True
        self.round_summaries = []  # History of past round summaries
        self.current_round_moves = {}  # player -> word mapping for current round
        self.players_done_current_round = set()  # Players who sent empty string

    

    def send_move(self, player : str, word : str):
        """Sends a given move from a given player.

        Raises ValueError if player doesn't exist.

        """
        if player not in self.players:
            raise ValueError(f"Player '{player}' doesn't exist")
        
        if not self.is_running:
            return  # Game is finished, ignore moves
        
        # Empty string means player is done with this round
        if word == "":
            self.players_done_current_round.add(player)
        else:
            # Check if word is longer than player's previous word in this round
            if player in self.current_round_moves:
                if len(word) <= len(self.current_round_moves[player]):
                    return  # Invalid move, ignore
            
            self.current_round_moves[player] = word
            # Remove player from done set if they make a move after saying they're done
            self.players_done_current_round.discard(player)
        
        # Check if all players are done with the round
        if len(self.players_done_current_round) == len(self.players):
            self._end_round()

    def get_state(self) -> Tuple[bool, int, List[str]]:
        """Returns the current game state.

        The returned values are
        - Whether the game is running
        - The current round number
        - The current history of summaries

        """
        # Return the last 3 summaries as current history
        current_history = self.round_summaries[-3:] if len(self.round_summaries) > 0 else []
        return self.is_running, self.current_round, current_history
    
    def _end_round(self):
        """End the current round and create summary."""
        # Create round summary
        if self.current_round_moves:
            summary_parts = []
            for player, word in self.current_round_moves.items():
                summary_parts.append(f"{player} played {word}")
            
            summary = f"On round {self.current_round}, " + " and ".join(summary_parts)
            self.round_summaries.append(summary)
        else:
            # No moves in this round, game is finished
            self.is_running = False
            return
        
        # Prepare for next round
        self.current_round += 1
        self.current_round_moves = {}
        self.players_done_current_round = set()
    
    
