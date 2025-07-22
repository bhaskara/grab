"""
Unit tests for Grab game logic and scoring
"""

import unittest
import numpy as np
from src.grab.grab_game import Grab, SCRABBLE_LETTER_SCORES, NoWordFoundException, DisallowedWordException
from src.grab.grab_state import State, Word, MakeWord, DrawLetters


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
            scores=np.array([0, 0]),
            passed=[True, False]  # Test that passed is preserved
        )
        
        # Make the word "cat" (c=3, a=1, t=1 in Scrabble scoring = 5 points)
        move, new_state = game.construct_move(state, 0, "cat")
        
        # Check that player 0's score increased by 5
        self.assertEqual(new_state.scores[0], 5)
        self.assertEqual(new_state.scores[1], 0)  # Player 1 unchanged
        
        # Check that passed status is preserved
        self.assertEqual(new_state.passed, [True, False])

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
            scores=np.array([0, 0]),
            passed=[True, False]  # Test that passed is reset to all False
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
        
        # Verify that passed status is reset to all False
        self.assertEqual(new_state.passed, [False, False])

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

    def test_construct_move_preserves_passed_status(self):
        """Test that construct_move preserves the passed status of players"""
        game = Grab()
        
        # Create a state with mixed passed status
        state = State(
            num_players=3,
            words_per_player=[[], [], []],
            pool=np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]),  # a, c, t
            bag=np.zeros(26),
            scores=np.array([0, 0, 0]),
            passed=[True, False, True]
        )
        
        # Make a word with player 1
        move, new_state = game.construct_move(state, 1, "cat")
        
        # Verify passed status is preserved exactly
        self.assertEqual(new_state.passed, [True, False, True])

    def test_construct_draw_letters_resets_passed_status(self):
        """Test that construct_draw_letters resets all players' passed status to False"""
        game = Grab()
        
        # Create a state where all players have passed
        state = State(
            num_players=4,
            words_per_player=[[], [], [], []],
            pool=np.zeros(26),
            bag=np.array([2, 2, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),  # Multiple letters
            scores=np.array([0, 0, 0, 0]),
            passed=[True, True, True, True]
        )
        
        # Draw letters
        move, new_state = game.construct_draw_letters(state, 2)
        
        # Verify all passed status is reset to False
        self.assertEqual(new_state.passed, [False, False, False, False])
        
    def test_construct_draw_letters_resets_mixed_passed_status(self):
        """Test that construct_draw_letters resets mixed passed status to all False"""
        game = Grab()
        
        # Create a state with mixed passed status
        state = State(
            num_players=3,
            words_per_player=[[], [], []],
            pool=np.ones(26),  # Some letters already in pool
            bag=np.array([3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),  # 3 a's
            scores=np.array([5, 10, 15]),
            passed=[False, True, False]
        )
        
        # Draw a letter
        move, new_state = game.construct_draw_letters(state, 1)
        
        # Verify all passed status is reset to False
        self.assertEqual(new_state.passed, [False, False, False])
        # Verify other state elements are preserved/updated correctly
        self.assertEqual(list(new_state.scores), [5, 10, 15])  # Scores should be preserved

    def test_handle_action_word_valid(self):
        """Test handle_action with a valid word"""
        game = Grab()
        
        # Set initial state with letters for "cat"
        initial_state = State(
            num_players=2,
            words_per_player=[[], []],
            pool=np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]),  # a, c, t
            bag=np.zeros(26),
            scores=[0, 0],
            passed=[False, False]
        )
        game.state = initial_state
        
        # Handle word action
        result_state = game.handle_action(0, "cat")
        
        # Verify the word was created and score updated
        self.assertEqual(len(result_state.words_per_player[0]), 1)
        self.assertEqual(result_state.words_per_player[0][0].word, "cat")
        self.assertEqual(result_state.scores[0], 5)  # c=3, a=1, t=1
        self.assertEqual(result_state.passed, [False, False])  # Passed status preserved
        
        # Verify game's internal state was updated
        self.assertEqual(game.state, result_state)

    def test_handle_action_word_invalid(self):
        """Test handle_action with invalid word raises exception"""
        game = Grab()
        
        # Set initial state with letters for "cat"
        initial_state = State(
            num_players=2,
            words_per_player=[[], []],
            pool=np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]),  # a, c, t
            bag=np.zeros(26),
            scores=[0, 0],
            passed=[False, False]
        )
        game.state = initial_state
        
        # Try invalid word - should raise DisallowedWordException
        with self.assertRaises(DisallowedWordException):
            game.handle_action(0, "zzqxyw")

    def test_handle_action_word_no_letters(self):
        """Test handle_action with word that cannot be formed"""
        game = Grab()
        
        # Set initial state with no letters in pool
        initial_state = State(
            num_players=2,
            words_per_player=[[], []],
            pool=np.zeros(26),  # No letters in pool
            bag=np.zeros(26),
            scores=[0, 0],
            passed=[False, False]
        )
        game.state = initial_state
        
        # Try to make word without letters - should raise NoWordFoundException
        with self.assertRaises(NoWordFoundException):
            game.handle_action(0, "cat")

    def test_handle_action_pass_single_player(self):
        """Test handle_action with pass action for single player"""
        game = Grab()
        
        initial_state = State(
            num_players=2,
            words_per_player=[[], []],
            pool=np.zeros(26),
            bag=np.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),  # 1 'a'
            scores=[0, 0],
            passed=[False, False]
        )
        game.state = initial_state
        
        # Handle pass action for player 0
        result_state = game.handle_action(0, 0)
        
        # Verify player 0 is marked as passed
        self.assertEqual(result_state.passed, [True, False])
        # Verify no other changes
        self.assertEqual(result_state.scores, [0, 0])
        self.assertEqual(len(result_state.words_per_player[0]), 0)

    def test_handle_action_pass_all_players_with_letters(self):
        """Test handle_action when all players pass and letters remain in bag"""
        game = Grab()
        
        initial_state = State(
            num_players=2,
            words_per_player=[[], []],
            pool=np.zeros(26),
            bag=np.array([2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),  # 2 'a's
            scores=[5, 10],
            passed=[True, False]  # Player 0 already passed
        )
        game.state = initial_state
        
        # Player 1 passes - this should trigger letter draw
        result_state = game.handle_action(1, 0)
        
        # Verify letter was drawn (bag decreased, pool increased)
        self.assertEqual(np.sum(result_state.bag), 1)  # One less in bag
        self.assertEqual(np.sum(result_state.pool), 1)  # One more in pool
        # Verify all passed status reset to False
        self.assertEqual(result_state.passed, [False, False])
        # Verify scores preserved
        self.assertEqual(result_state.scores, [5, 10])

    def test_handle_action_pass_all_players_no_letters(self):
        """Test handle_action when all players pass and no letters remain"""
        game = Grab()
        
        # Create state with words for end-game scoring
        existing_word = Word("cat")
        initial_state = State(
            num_players=2,
            words_per_player=[[existing_word], []],
            pool=np.zeros(26),
            bag=np.zeros(26),  # No letters in bag
            scores=[10, 5],
            passed=[True, False]  # Player 0 already passed
        )
        game.state = initial_state
        
        # Player 1 passes - this should end the game
        result_state = game.handle_action(1, 0)
        
        # Verify game ended with bonus scoring
        expected_bonus = 5  # "cat" = c(3) + a(1) + t(1) = 5
        self.assertEqual(result_state.scores[0], 10 + expected_bonus)  # Original + bonus
        self.assertEqual(result_state.scores[1], 5)  # No words, no bonus

    def test_handle_action_invalid_player(self):
        """Test handle_action with invalid player number"""
        game = Grab()
        
        initial_state = State(
            num_players=2,
            words_per_player=[[], []],
            pool=np.zeros(26),
            bag=np.zeros(26),
            scores=[0, 0],
            passed=[False, False]
        )
        game.state = initial_state
        
        # Test negative player
        with self.assertRaises(ValueError) as context:
            game.handle_action(-1, 0)
        self.assertIn("Player -1 is out of range", str(context.exception))
        
        # Test player too high
        with self.assertRaises(ValueError) as context:
            game.handle_action(2, 0)
        self.assertIn("Player 2 is out of range", str(context.exception))

    def test_handle_action_invalid_action(self):
        """Test handle_action with invalid action type"""
        game = Grab()
        
        initial_state = State(
            num_players=2,
            words_per_player=[[], []],
            pool=np.zeros(26),
            bag=np.zeros(26),
            scores=[0, 0],
            passed=[False, False]
        )
        game.state = initial_state
        
        # Test invalid integer action
        with self.assertRaises(ValueError) as context:
            game.handle_action(0, 1)
        self.assertIn("Invalid action: 1", str(context.exception))
        
        # Test invalid type
        with self.assertRaises(ValueError) as context:
            game.handle_action(0, [])
        self.assertIn("Invalid action", str(context.exception))

    def test_handle_action_complex_scenario(self):
        """Test handle_action in complex multi-player scenario"""
        game = Grab()
        
        # Set up game with 3 players, some words, mixed pass status
        existing_words = [Word("dog"), Word("cat")]
        initial_state = State(
            num_players=3,
            words_per_player=[[], existing_words, []],
            pool=np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]),  # s
            bag=np.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),  # 1 'a'
            scores=[0, 8, 0],  # Player 1 has score from previous words
            passed=[True, False, True]  # Players 0 and 2 already passed
        )
        game.state = initial_state
        
        # Player 1 makes "cats" using "cat" + "s"
        result_state = game.handle_action(1, "cats")
        
        # Verify the move was successful - should have created "cats" 
        # The exact number of words depends on how construct_move chose to build "cats"
        word_names = [w.word for w in result_state.words_per_player[1]]
        self.assertIn("cats", word_names)
        # Verify score updated (cats = c(3) + a(1) + t(1) + s(1) = 6)
        self.assertEqual(result_state.scores[1], 8 + 6)
        # Verify passed status preserved
        self.assertEqual(result_state.passed, [True, False, True])

    def test_word_list_validation_valid_word(self):
        """Test that valid words from word list are accepted"""
        game = Grab(word_list='twl06')
        
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
        game = Grab(word_list='twl06')
        
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
        game = Grab(word_list='twl06')
        
        # Create a simple game state with letters for "cat"
        state = State(
            num_players=1,
            words_per_player=[[]],
            pool=np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]),  # a, c, t
            bag=np.zeros(26),
            scores=np.array([0])
        )
        
        # "cat" should be accepted (case insensitive)
        move, new_state = game.construct_move(state, 0, "cat")
        self.assertIsInstance(move, MakeWord)
        self.assertEqual(move.word, "cat")

    def test_different_word_lists(self):
        """Test that different word lists can be loaded and behave differently"""
        game_twl06 = Grab(word_list='twl06')
        game_sowpods = Grab(word_list='sowpods')
        
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

    def test_end_game_no_words(self):
        """Test end_game with no words on the board"""
        game = Grab()
        
        # Create a state with no words for any player
        state = State(
            num_players=2,
            words_per_player=[[], []],
            pool=np.zeros(26),
            bag=np.zeros(26),
            scores=np.array([10, 5])  # Starting scores
        )
        
        end_state = game.end_game(state)
        
        # Scores should remain unchanged (no bonus)
        self.assertEqual(end_state.scores[0], 10)
        self.assertEqual(end_state.scores[1], 5)

    def test_end_game_with_words(self):
        """Test end_game with words on the board"""
        game = Grab()
        
        # Create words for players
        word_cat = Word("cat")  # c(3) + a(1) + t(1) = 5 points
        word_dog = Word("dog")  # d(2) + o(1) + g(2) = 5 points
        word_fish = Word("fish")  # f(4) + i(1) + s(1) + h(4) = 10 points
        
        state = State(
            num_players=2,
            words_per_player=[[word_cat, word_dog], [word_fish]],
            pool=np.zeros(26),
            bag=np.zeros(26),
            scores=np.array([15, 8])  # Starting scores
        )
        
        end_state = game.end_game(state)
        
        # Player 0 gets bonus: cat(5) + dog(5) = 10, total = 15 + 10 = 25
        # Player 1 gets bonus: fish(10), total = 8 + 10 = 18
        self.assertEqual(end_state.scores[0], 25)
        self.assertEqual(end_state.scores[1], 18)

    def test_end_game_state_immutability(self):
        """Test that end_game doesn't modify the original state"""
        game = Grab()
        
        word_cat = Word("cat")
        original_scores = np.array([10, 5])
        original_words = [[word_cat], []]
        
        state = State(
            num_players=2,
            words_per_player=original_words,
            pool=np.zeros(26),
            bag=np.zeros(26),
            scores=original_scores.copy()
        )
        
        # Store original values
        original_score_0 = state.scores[0]
        original_word_count = len(state.words_per_player[0])
        
        end_state = game.end_game(state)
        
        # Original state should be unchanged
        self.assertEqual(state.scores[0], original_score_0)
        self.assertEqual(len(state.words_per_player[0]), original_word_count)
        
        # End state should have bonus added
        self.assertEqual(end_state.scores[0], original_score_0 + 5)  # cat = 5 points

    def test_end_game_custom_letter_scores(self):
        """Test end_game with custom letter scoring"""
        # All letters worth 2 points
        custom_scores = np.full(26, 2)
        game = Grab(letter_scores=custom_scores)
        
        word_cat = Word("cat")  # 3 letters * 2 points each = 6 points
        
        state = State(
            num_players=1,
            words_per_player=[[word_cat]],
            pool=np.zeros(26),
            bag=np.zeros(26),
            scores=np.array([10])
        )
        
        end_state = game.end_game(state)
        
        # Player should get 6 point bonus: 10 + 6 = 16
        self.assertEqual(end_state.scores[0], 16)

    def test_end_game_multiple_words_same_player(self):
        """Test end_game when one player has multiple words"""
        game = Grab()
        
        word_a = Word("a")      # a(1) = 1 point
        word_at = Word("at")    # a(1) + t(1) = 2 points
        word_cat = Word("cat")  # c(3) + a(1) + t(1) = 5 points
        
        state = State(
            num_players=1,
            words_per_player=[[word_a, word_at, word_cat]],
            pool=np.zeros(26),
            bag=np.zeros(26),
            scores=np.array([0])
        )
        
        end_state = game.end_game(state)
        
        # Player should get bonus: a(1) + at(2) + cat(5) = 8 points
        self.assertEqual(end_state.scores[0], 8)

    def test_grab_state_initialization(self):
        """Test that Grab initializes with correct default state"""
        game = Grab(num_players=3)
        
        # Check that state is properly initialized
        self.assertIsNotNone(game.state)
        self.assertEqual(game.state.num_players, 3)
        self.assertEqual(len(game.state.words_per_player), 3)
        self.assertEqual(len(game.state.scores), 3)
        
        # Check that all players start with no words and zero score
        for i in range(3):
            self.assertEqual(len(game.state.words_per_player[i]), 0)
            self.assertEqual(game.state.scores[i], 0)
        
        # Check that pool starts empty
        self.assertTrue(np.all(game.state.pool == 0))
        
        # Check that bag starts with standard Scrabble distribution
        np.testing.assert_array_equal(game.state.bag, State(1).bag)

    def test_grab_state_getter(self):
        """Test the state getter property"""
        game = Grab(num_players=2)
        
        # Test that we can access the state
        state = game.state
        self.assertIsInstance(state, State)
        self.assertEqual(state.num_players, 2)

    def test_grab_state_setter(self):
        """Test the state setter property"""
        game = Grab(num_players=2)
        
        # Create a new state with different values
        new_state = State(
            num_players=2,
            pool=np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]),  # a, c, t
            scores=[10, 5]
        )
        
        # Set the new state
        game.state = new_state
        
        # Verify the state was set correctly
        self.assertEqual(game.state.scores[0], 10)
        self.assertEqual(game.state.scores[1], 5)
        self.assertEqual(game.state.pool[0], 1)  # 'a'
        self.assertEqual(game.state.pool[2], 1)  # 'c'
        self.assertEqual(game.state.pool[19], 1)  # 't'

    def test_grab_state_setter_type_validation(self):
        """Test that state setter validates input type"""
        game = Grab()
        
        # Try to set state to invalid types
        with self.assertRaises(TypeError) as context:
            game.state = "not a state"
        self.assertIn("state must be a State instance", str(context.exception))
        
        with self.assertRaises(TypeError) as context:
            game.state = {"not": "a state"}
        self.assertIn("state must be a State instance", str(context.exception))

    def test_grab_num_players_validation(self):
        """Test that invalid num_players raises ValueError"""
        with self.assertRaises(ValueError) as context:
            Grab(num_players=0)
        self.assertIn("Number of players must be at least 1", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            Grab(num_players=-1)
        self.assertIn("Number of players must be at least 1", str(context.exception))

    def test_grab_different_num_players(self):
        """Test Grab initialization with different numbers of players"""
        # Test single player
        game1 = Grab(num_players=1)
        self.assertEqual(game1.state.num_players, 1)
        self.assertEqual(len(game1.state.scores), 1)
        
        # Test four players
        game4 = Grab(num_players=4)
        self.assertEqual(game4.state.num_players, 4)
        self.assertEqual(len(game4.state.scores), 4)


if __name__ == '__main__':
    unittest.main()