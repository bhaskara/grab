"""
Unit tests for Grab game logic and scoring
"""

import unittest
import numpy as np
from src.grab.grab_game import Grab, SCRABBLE_LETTER_SCORES
from src.grab.grab_state import State, Word, Move, NoWordFoundException


class TestGrab(unittest.TestCase):
    """Test cases for Grab game logic"""

    def test_grab_default_letter_scores(self):
        """Test that Grab uses default Scrabble letter scores"""
        game = Grab()
        np.testing.assert_array_equal(game.letter_scores, SCRABBLE_LETTER_SCORES)

    def test_grab_custom_letter_scores(self):
        """Test that Grab accepts custom letter scores"""
        custom_scores = np.ones(26)  # All letters worth 1 point
        game = Grab(letter_scores=custom_scores)
        np.testing.assert_array_equal(game.letter_scores, custom_scores)

    def test_grab_invalid_letter_scores_length(self):
        """Test that Grab rejects invalid letter scores array length"""
        with self.assertRaises(ValueError) as context:
            Grab(letter_scores=np.array([1, 2, 3]))  # Wrong length
        
        self.assertIn("length-26 array", str(context.exception))

    def test_construct_move_scoring_default(self):
        """Test that construct_move calculates scores correctly with default Scrabble values"""
        game = Grab()
        
        # Create a simple game state with 2 players
        # Player 0 has no words, pool has letters for "cat"
        state = State(
            num_players=2,
            words_per_player=[[], []],
            pool=np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]),  # a, c, t
            bag=np.zeros(26),
            scores=np.array([0, 0])
        )
        
        # Make the word "cat" (c=3, a=1, t=1 in Scrabble scoring = 5 points)
        move, new_state = game.construct_move(state, 0, "cat")
        
        # Check that player 0's score increased by 5
        self.assertEqual(new_state.scores[0], 5)
        self.assertEqual(new_state.scores[1], 0)  # Player 1 unchanged

    def test_construct_move_scoring_custom(self):
        """Test that construct_move calculates scores correctly with custom letter values"""
        # Custom scoring where all letters are worth 2 points
        custom_scores = np.full(26, 2)
        game = Grab(letter_scores=custom_scores)
        
        # Create a simple game state
        state = State(
            num_players=1,
            words_per_player=[[]],
            pool=np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]),  # a, c, t
            bag=np.zeros(26),
            scores=np.array([0])
        )
        
        # Make the word "cat" (3 letters * 2 points each = 6 points)
        move, new_state = game.construct_move(state, 0, "cat")
        
        # Check that player's score increased by 6
        self.assertEqual(new_state.scores[0], 6)

    def test_construct_move_scoring_with_reused_word(self):
        """Test scoring when reusing another player's word"""
        game = Grab()
        
        # Create a state where player 1 has the word "cat"
        # Pool has letter "s" to make "cats"
        existing_word = Word("cat")
        state = State(
            num_players=2,
            words_per_player=[[], [existing_word]],
            pool=np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]),  # s
            bag=np.zeros(26),
            scores=np.array([0, 5])  # Player 1 already has 5 points from "cat"
        )
        
        # Player 0 makes "cats" using player 1's "cat" + "s" from pool
        # "cats" = c(3) + a(1) + t(1) + s(1) = 6 points
        move, new_state = game.construct_move(state, 0, "cats")
        
        # Check that player 0 gets 6 points for "cats"
        self.assertEqual(new_state.scores[0], 6)
        # Player 1's score should remain unchanged (they lost their word but keep their score)
        self.assertEqual(new_state.scores[1], 5)
        
        # Verify the word was moved correctly
        self.assertEqual(len(new_state.words_per_player[0]), 1)
        self.assertEqual(new_state.words_per_player[0][0].word, "cats")
        self.assertEqual(len(new_state.words_per_player[1]), 0)

    def test_construct_move_high_value_word(self):
        """Test scoring with a high-value word containing Q and Z"""
        game = Grab()
        
        # Create state with letters for "quiz" in pool
        # q=10, u=1, i=1, z=10 = 22 points
        state = State(
            num_players=1,
            words_per_player=[[]],
            pool=np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1]),  # i, q, u, z
            bag=np.zeros(26),
            scores=np.array([0])
        )
        
        move, new_state = game.construct_move(state, 0, "quiz")
        
        # Check that score is 22 points
        self.assertEqual(new_state.scores[0], 22)

    def test_scrabble_letter_scores_constant(self):
        """Test that the SCRABBLE_LETTER_SCORES constant has correct values"""
        # Verify the constant has the right length
        self.assertEqual(len(SCRABBLE_LETTER_SCORES), 26)
        
        # Test a few known Scrabble values
        self.assertEqual(SCRABBLE_LETTER_SCORES[0], 1)   # A = 1
        self.assertEqual(SCRABBLE_LETTER_SCORES[16], 10) # Q = 10
        self.assertEqual(SCRABBLE_LETTER_SCORES[25], 10) # Z = 10
        self.assertEqual(SCRABBLE_LETTER_SCORES[9], 8)   # J = 8


if __name__ == '__main__':
    unittest.main()