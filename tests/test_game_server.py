"""
Unit tests for the GameServer class.
"""

import pytest
from src.grab.game_server import GameServer


class TestGameServer:
    """Test cases for GameServer class methods."""

    def setup_method(self):
        """Set up a fresh GameServer instance for each test."""
        self.server = GameServer()

    def test_init(self):
        """Test GameServer initialization."""
        server = GameServer()
        assert server is not None

    def test_add_player_success(self):
        """Test successful player addition."""
        self.server.add_player("Alice")
        players = self.server.list_players()
        assert "Alice" in players

    def test_add_player_duplicate_raises_error(self):
        """Test that adding duplicate player raises RuntimeError."""
        self.server.add_player("Alice")
        with pytest.raises(RuntimeError):
            self.server.add_player("Alice")

    def test_list_players_empty_initially(self):
        """Test that player list is empty initially."""
        players = self.server.list_players()
        assert players == []

    def test_list_players_multiple(self):
        """Test listing multiple players."""
        self.server.add_player("Alice")
        self.server.add_player("Bob")
        self.server.add_player("Charlie")
        players = self.server.list_players()
        assert len(players) == 3
        assert "Alice" in players
        assert "Bob" in players
        assert "Charlie" in players

    def test_list_games_empty_initially(self):
        """Test that game list is empty initially."""
        games = self.server.list_games()
        assert games == []

    def test_add_game_returns_id(self):
        """Test that adding a game returns a string ID."""
        game_id = self.server.add_game()
        assert isinstance(game_id, str)
        assert game_id != ""

    def test_add_game_consecutive_ids(self):
        """Test that game IDs are consecutive integers as strings."""
        game_id1 = self.server.add_game()
        game_id2 = self.server.add_game()
        game_id3 = self.server.add_game()
        
        # Should be consecutive integers
        assert int(game_id2) == int(game_id1) + 1
        assert int(game_id3) == int(game_id2) + 1

    def test_list_games_after_adding(self):
        """Test that added games appear in the list."""
        game_id1 = self.server.add_game()
        game_id2 = self.server.add_game()
        
        games = self.server.list_games()
        assert game_id1 in games
        assert game_id2 in games
        assert len(games) == 2

    def test_get_game_info_new_game(self):
        """Test getting info for a newly created game."""
        game_id = self.server.add_game()
        status, players = self.server.get_game_info(game_id)
        assert status == "setup"  # New games should be in setup state
        assert players == []

    def test_get_game_info_nonexistent_game(self):
        """Test that getting info for nonexistent game raises KeyError."""
        with pytest.raises(KeyError):
            self.server.get_game_info("nonexistent")

    def test_add_player_to_game_success(self):
        """Test successfully adding a player to a game."""
        self.server.add_player("Alice")
        game_id = self.server.add_game()
        
        self.server.add_player_to_game("Alice", game_id)
        
        status, players = self.server.get_game_info(game_id)
        assert "Alice" in players

    def test_add_player_to_game_nonexistent_player(self):
        """Test that adding nonexistent player to game raises KeyError."""
        game_id = self.server.add_game()
        with pytest.raises(KeyError):
            self.server.add_player_to_game("NonexistentPlayer", game_id)

    def test_add_player_to_game_nonexistent_game(self):
        """Test that adding player to nonexistent game raises KeyError."""
        self.server.add_player("Alice")
        with pytest.raises(KeyError):
            self.server.add_player_to_game("Alice", "nonexistent")

    def test_add_player_to_game_complete_game_raises_error(self):
        """Test that adding player to complete game raises RuntimeError."""
        self.server.add_player("Alice")
        game_id = self.server.add_game()
        self.server.set_game_state(game_id, "done")
        
        with pytest.raises(RuntimeError):
            self.server.add_player_to_game("Alice", game_id)

    def test_add_player_to_multiple_games_raises_error(self):
        """Test that adding player to multiple games raises RuntimeError."""
        self.server.add_player("Alice")
        game_id1 = self.server.add_game()
        game_id2 = self.server.add_game()
        
        self.server.add_player_to_game("Alice", game_id1)
        
        with pytest.raises(RuntimeError):
            self.server.add_player_to_game("Alice", game_id2)

    def test_remove_game_success(self):
        """Test successfully removing a game."""
        game_id = self.server.add_game()
        assert game_id in self.server.list_games()
        
        self.server.remove_game(game_id)
        assert game_id not in self.server.list_games()

    def test_remove_nonexistent_game(self):
        """Test that removing nonexistent game handles gracefully."""
        # Should not raise an error based on the method signature
        self.server.remove_game("nonexistent")

    def test_set_game_state_success(self):
        """Test successfully setting game state."""
        game_id = self.server.add_game()
        
        self.server.set_game_state(game_id, "running")
        status, _ = self.server.get_game_info(game_id)
        assert status == "running"
        
        self.server.set_game_state(game_id, "paused")
        status, _ = self.server.get_game_info(game_id)
        assert status == "paused"
        
        self.server.set_game_state(game_id, "done")
        status, _ = self.server.get_game_info(game_id)
        assert status == "done"

    def test_set_game_state_nonexistent_game(self):
        """Test that setting state for nonexistent game raises KeyError."""
        with pytest.raises(KeyError):
            self.server.set_game_state("nonexistent", "running")

    def test_set_game_state_invalid_state(self):
        """Test that setting invalid game state raises ValueError."""
        game_id = self.server.add_game()
        
        with pytest.raises(ValueError):
            self.server.set_game_state(game_id, "invalid_state")

    def test_valid_game_states(self):
        """Test all valid game states can be set."""
        game_id = self.server.add_game()
        valid_states = ["setup", "running", "paused", "done"]
        
        for state in valid_states:
            self.server.set_game_state(game_id, state)
            status, _ = self.server.get_game_info(game_id)
            assert status == state

    def test_multiple_players_in_game(self):
        """Test adding multiple players to the same game."""
        self.server.add_player("Alice")
        self.server.add_player("Bob")
        self.server.add_player("Charlie")
        game_id = self.server.add_game()
        
        self.server.add_player_to_game("Alice", game_id)
        self.server.add_player_to_game("Bob", game_id)
        self.server.add_player_to_game("Charlie", game_id)
        
        status, players = self.server.get_game_info(game_id)
        assert len(players) == 3
        assert "Alice" in players
        assert "Bob" in players
        assert "Charlie" in players

    def test_player_removed_when_game_removed(self):
        """Test that players are freed when their game is removed."""
        self.server.add_player("Alice")
        game_id1 = self.server.add_game()
        game_id2 = self.server.add_game()
        
        self.server.add_player_to_game("Alice", game_id1)
        self.server.remove_game(game_id1)
        
        # Alice should now be able to join another game
        self.server.add_player_to_game("Alice", game_id2)
        status, players = self.server.get_game_info(game_id2)
        assert "Alice" in players