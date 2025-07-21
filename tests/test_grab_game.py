"""
Unit tests for Grab game logic and scoring
"""

import unittest
import numpy as np
from src.grab.grab_game import Grab, SCRABBLE_LETTER_SCORES
from src.grab.grab_state import State, Word, MakeWord, DrawLetters, NoWordFoundException, DisallowedWordException


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

    def test_construct_draw_letters_single_letter(self):
        """Test drawing a single letter from the bag"""
        game = Grab()
        
        # Create a state with specific letters in the bag
        state = State(
            num_players=2,
            words_per_player=[[], []],
            pool=np.zeros(26),
            bag=np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]),  # a, c, t
            scores=np.array([0, 0])
        )
        
        # Draw one letter
        move, new_state = game.construct_draw_letters(state, 1)
        
        # Verify the move contains exactly one letter
        self.assertIsInstance(move, DrawLetters)
        self.assertEqual(len(move.letters), 1)
        self.assertIn(move.letters[0], ['a', 'c', 't'])
        
        # Verify the state changes correctly
        self.assertEqual(np.sum(new_state.bag), 2)  # One less letter in bag
        self.assertEqual(np.sum(new_state.pool), 1)  # One more letter in pool
        
        # Verify the drawn letter was moved from bag to pool
        drawn_letter = move.letters[0]
        letter_idx = ord(drawn_letter) - ord('a')
        self.assertEqual(new_state.bag[letter_idx], state.bag[letter_idx] - 1)
        self.assertEqual(new_state.pool[letter_idx], state.pool[letter_idx] + 1)

    def test_construct_draw_letters_multiple_letters(self):
        """Test drawing multiple letters from the bag"""
        game = Grab()
        
        # Create a state with more letters in the bag
        state = State(
            num_players=1,
            words_per_player=[[]],
            pool=np.zeros(26),
            bag=np.array([3, 2, 2, 1, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0]),  # 14 total letters
            scores=np.array([0])
        )
        
        # Draw three letters
        move, new_state = game.construct_draw_letters(state, 3)
        
        # Verify the move contains exactly three letters
        self.assertIsInstance(move, DrawLetters)
        self.assertEqual(len(move.letters), 3)
        
        # Verify the state changes correctly
        self.assertEqual(np.sum(new_state.bag), 11)  # Three less letters in bag
        self.assertEqual(np.sum(new_state.pool), 3)  # Three more letters in pool

    def test_construct_draw_letters_empty_bag(self):
        """Test that drawing from an empty bag raises ValueError"""
        game = Grab()
        
        # Create a state with empty bag
        state = State(
            num_players=1,
            words_per_player=[[]],
            pool=np.zeros(26),
            bag=np.zeros(26),  # Empty bag
            scores=np.array([0])
        )
        
        # Attempt to draw a letter should raise ValueError
        with self.assertRaises(ValueError) as context:
            game.construct_draw_letters(state, 1)
        
        self.assertIn("Not enough letters in bag", str(context.exception))

    def test_construct_draw_letters_insufficient_letters(self):
        """Test drawing more letters than available raises ValueError"""
        game = Grab()
        
        # Create a state with only 2 letters in bag
        state = State(
            num_players=1,
            words_per_player=[[]],
            pool=np.zeros(26),
            bag=np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),  # a, c
            scores=np.array([0])
        )
        
        # Attempt to draw 3 letters should raise ValueError
        with self.assertRaises(ValueError) as context:
            game.construct_draw_letters(state, 3)
        
        self.assertIn("Not enough letters in bag", str(context.exception))

    def test_construct_draw_letters_invalid_num_letters(self):
        """Test that requesting zero or negative letters raises ValueError"""
        game = Grab()
        
        state = State(
            num_players=1,
            words_per_player=[[]],
            pool=np.zeros(26),
            bag=np.array([5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),  # 5 a's
            scores=np.array([0])
        )
        
        # Test zero letters
        with self.assertRaises(ValueError) as context:
            game.construct_draw_letters(state, 0)
        self.assertIn("must be positive", str(context.exception))
        
        # Test negative letters
        with self.assertRaises(ValueError) as context:
            game.construct_draw_letters(state, -1)
        self.assertIn("must be positive", str(context.exception))

    def test_construct_draw_letters_state_immutability(self):
        """Test that the original state is not modified"""
        game = Grab()
        
        original_bag = np.array([2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        original_pool = np.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        
        state = State(
            num_players=1,
            words_per_player=[[]],
            pool=original_pool.copy(),
            bag=original_bag.copy(),
            scores=np.array([0])
        )
        
        # Draw a letter
        move, new_state = game.construct_draw_letters(state, 1)
        
        # Verify original state is unchanged
        np.testing.assert_array_equal(state.bag, original_bag)
        np.testing.assert_array_equal(state.pool, original_pool)
        
        # Verify new state is different
        self.assertFalse(np.array_equal(new_state.bag, original_bag))
        self.assertFalse(np.array_equal(new_state.pool, original_pool))

    def test_word_list_validation_valid_word(self):
        """Test that valid words from word list are accepted"""
        game = Grab('twl06')
        
        # Create a simple game state with letters for "cat" (should be in word list)
        state = State(
            num_players=1,
            words_per_player=[[]],
            pool=np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]),  # a, c, t
            bag=np.zeros(26),
            scores=np.array([0])
        )
        
        # "cat" should be valid and not raise exception
        move, new_state = game.construct_move(state, 0, "cat")
        self.assertIsInstance(move, MakeWord)
        self.assertEqual(move.word, "cat")

    def test_word_list_validation_invalid_word(self):
        """Test that invalid words not in word list are rejected"""
        game = Grab('twl06')
        
        # Create a simple game state with letters for "xyz" (should not be in word list)
        state = State(
            num_players=1,
            words_per_player=[[]],
            pool=np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1]),  # x, y, z
            bag=np.zeros(26),
            scores=np.array([0])
        )
        
        # "xyz" should raise DisallowedWordException
        with self.assertRaises(DisallowedWordException) as context:
            game.construct_move(state, 0, "xyz")
        
        self.assertEqual(context.exception.word, "xyz")
        self.assertIn("not in the allowed word list", str(context.exception))

    def test_word_list_validation_case_insensitive(self):
        """Test that word validation is case insensitive"""
        game = Grab('twl06')
        
        # Create a simple game state with letters for "CAT"
        state = State(
            num_players=1,
            words_per_player=[[]],
            pool=np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]),  # a, c, t
            bag=np.zeros(26),
            scores=np.array([0])
        )
        
        # "CAT" should be accepted (case insensitive)
        move, new_state = game.construct_move(state, 0, "CAT")
        self.assertIsInstance(move, MakeWord)
        self.assertEqual(move.word, "CAT")

    def test_different_word_lists(self):
        """Test that different word lists can be loaded and behave differently"""
        game_twl06 = Grab('twl06')
        game_sowpods = Grab('sowpods')
        
        # Both should have loaded word lists
        self.assertIsNotNone(game_twl06.valid_words)
        self.assertIsNotNone(game_sowpods.valid_words)
        self.assertIsInstance(game_twl06.valid_words, set)
        self.assertIsInstance(game_sowpods.valid_words, set)
        
        # "ch" is in SOWPODS but not TWL06
        state = State(
            num_players=1,
            words_per_player=[[]],
            pool=np.array([0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),  # c, h
            bag=np.zeros(26),
            scores=np.array([0])
        )
        
        # "ch" should work with SOWPODS but fail with TWL06
        move, new_state = game_sowpods.construct_move(state, 0, "ch")
        self.assertIsInstance(move, MakeWord)
        self.assertEqual(move.word, "ch")
        
        with self.assertRaises(DisallowedWordException):
            game_twl06.construct_move(state, 0, "ch")


if __name__ == '__main__':
    unittest.main()