"""
Unit tests for grab_state module
"""

import unittest
import numpy as np
from src.grab.grab_state import Word, State, MakeWord, DrawLetters, STANDARD_SCRABBLE_DISTRIBUTION


class TestWord(unittest.TestCase):
    """Test cases for the Word class"""

    def test_word_creation_simple(self):
        """Test creating a Word with a simple word"""
        word = Word("cat")
        self.assertEqual(word.word, "cat")
        self.assertEqual(word.letter_counts.shape, (26,))
        self.assertEqual(word.letter_counts.dtype, int)
        
        # Check specific letter counts
        # c=2, a=0, t=19
        expected_counts = np.zeros(26, dtype=int)
        expected_counts[2] = 1  # c
        expected_counts[0] = 1  # a
        expected_counts[19] = 1  # t
        np.testing.assert_array_equal(word.letter_counts, expected_counts)

    def test_word_creation_with_repeated_letters(self):
        """Test creating a Word with repeated letters"""
        word = Word("moon")
        self.assertEqual(word.word, "moon")
        
        # Check specific letter counts
        # m=12, o=14, n=13
        expected_counts = np.zeros(26, dtype=int)
        expected_counts[12] = 1  # m
        expected_counts[14] = 2  # o (appears twice)
        expected_counts[13] = 1  # n
        np.testing.assert_array_equal(word.letter_counts, expected_counts)

    def test_word_creation_uppercase(self):
        """Test creating a Word with uppercase letters"""
        word = Word("HELLO")
        self.assertEqual(word.word, "hello")
        
        # Check specific letter counts
        # h=7, e=4, l=11, o=14
        expected_counts = np.zeros(26, dtype=int)
        expected_counts[7] = 1   # h
        expected_counts[4] = 1   # e
        expected_counts[11] = 2  # l (appears twice)
        expected_counts[14] = 1  # o
        np.testing.assert_array_equal(word.letter_counts, expected_counts)

    def test_word_creation_mixed_case(self):
        """Test creating a Word with mixed case letters"""
        word = Word("WoRlD")
        self.assertEqual(word.word, "world")
        
        # Check specific letter counts
        # w=22, o=14, r=17, l=11, d=3
        expected_counts = np.zeros(26, dtype=int)
        expected_counts[22] = 1  # w
        expected_counts[14] = 1  # o
        expected_counts[17] = 1  # r
        expected_counts[11] = 1  # l
        expected_counts[3] = 1   # d
        np.testing.assert_array_equal(word.letter_counts, expected_counts)

    def test_word_creation_empty_string(self):
        """Test creating a Word with an empty string"""
        word = Word("")
        self.assertEqual(word.word, "")
        
        # All counts should be zero
        expected_counts = np.zeros(26, dtype=int)
        np.testing.assert_array_equal(word.letter_counts, expected_counts)

    def test_word_creation_invalid_character_number(self):
        """Test creating a Word with a number should raise ValueError"""
        with self.assertRaises(ValueError) as context:
            Word("hello1")
        self.assertIn("invalid character: '1'", str(context.exception))

    def test_word_creation_invalid_character_space(self):
        """Test creating a Word with a space should raise ValueError"""
        with self.assertRaises(ValueError) as context:
            Word("hello world")
        self.assertIn("invalid character: ' '", str(context.exception))

    def test_word_creation_invalid_character_punctuation(self):
        """Test creating a Word with punctuation should raise ValueError"""
        with self.assertRaises(ValueError) as context:
            Word("hello!")
        self.assertIn("invalid character: '!'", str(context.exception))

    def test_word_creation_invalid_character_special(self):
        """Test creating a Word with special characters should raise ValueError"""
        with self.assertRaises(ValueError) as context:
            Word("hello@world")
        self.assertIn("invalid character: '@'", str(context.exception))

    def test_letter_counts_sum_equals_word_length(self):
        """Test that the sum of letter counts equals the word length"""
        test_words = ["cat", "hello", "programming", "a", "supercalifragilisticexpialidocious"]
        
        for test_word in test_words:
            word = Word(test_word)
            self.assertEqual(np.sum(word.letter_counts), len(test_word))

    def test_all_alphabet_letters(self):
        """Test creating a Word with all alphabet letters"""
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        word = Word(alphabet)
        self.assertEqual(word.word, alphabet)
        
        # Each letter should appear exactly once
        expected_counts = np.ones(26, dtype=int)
        np.testing.assert_array_equal(word.letter_counts, expected_counts)


class TestState(unittest.TestCase):
    """Test cases for the State class"""

    def test_state_creation_minimal(self):
        """Test creating a State with minimal parameters"""
        state = State(num_players=2)
        
        self.assertEqual(state.num_players, 2)
        self.assertEqual(len(state.words_per_player), 2)
        self.assertEqual(len(state.scores), 2)
        
        # Check that each player has empty word list
        for player_words in state.words_per_player:
            self.assertEqual(len(player_words), 0)
            self.assertIsInstance(player_words, list)
        
        # Check scores are all zero
        self.assertEqual(state.scores, [0, 0])
        
        # Check pool is empty
        np.testing.assert_array_equal(state.pool, np.zeros(26, dtype=int))
        
        # Check bag has standard distribution
        np.testing.assert_array_equal(state.bag, STANDARD_SCRABBLE_DISTRIBUTION)

    def test_state_creation_with_custom_parameters(self):
        """Test creating a State with all custom parameters"""
        custom_words = [[], [Word("cat"), Word("dog")]]
        custom_pool = np.ones(26, dtype=int)
        custom_bag = np.full(26, 5, dtype=int)
        custom_scores = [10, 20]
        
        state = State(
            num_players=2,
            words_per_player=custom_words,
            pool=custom_pool,
            bag=custom_bag,
            scores=custom_scores
        )
        
        self.assertEqual(state.num_players, 2)
        self.assertEqual(len(state.words_per_player[0]), 0)
        self.assertEqual(len(state.words_per_player[1]), 2)
        self.assertEqual(state.scores, [10, 20])
        np.testing.assert_array_equal(state.pool, custom_pool)
        np.testing.assert_array_equal(state.bag, custom_bag)

    def test_state_creation_invalid_num_players(self):
        """Test creating a State with invalid number of players"""
        with self.assertRaises(ValueError) as context:
            State(num_players=0)
        self.assertIn("Number of players must be at least 1", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            State(num_players=-1)
        self.assertIn("Number of players must be at least 1", str(context.exception))

    def test_state_creation_mismatched_words_per_player(self):
        """Test creating a State with wrong length words_per_player"""
        with self.assertRaises(ValueError) as context:
            State(num_players=3, words_per_player=[[], []])  # Only 2 lists for 3 players
        self.assertIn("words_per_player must have length 3, got 2", str(context.exception))

    def test_state_creation_mismatched_scores(self):
        """Test creating a State with wrong length scores"""
        with self.assertRaises(ValueError) as context:
            State(num_players=2, scores=[10, 20, 30])  # 3 scores for 2 players
        self.assertIn("scores must have length 2, got 3", str(context.exception))

    def test_state_creation_invalid_pool_shape(self):
        """Test creating a State with wrong pool shape"""
        with self.assertRaises(ValueError) as context:
            State(num_players=2, pool=np.zeros(25, dtype=int))  # Wrong size
        self.assertIn("pool must be an array of 26 integers", str(context.exception))

    def test_state_creation_invalid_bag_shape(self):
        """Test creating a State with wrong bag shape"""
        with self.assertRaises(ValueError) as context:
            State(num_players=2, bag=np.zeros(27, dtype=int))  # Wrong size
        self.assertIn("bag must be an array of 26 integers", str(context.exception))

    def test_state_arrays_are_copied(self):
        """Test that input arrays are copied, not referenced"""
        original_pool = np.ones(26, dtype=int)
        original_bag = np.full(26, 5, dtype=int)
        original_scores = [10, 20]
        
        state = State(
            num_players=2,
            pool=original_pool,
            bag=original_bag,
            scores=original_scores
        )
        
        # Modify originals
        original_pool[0] = 999
        original_bag[0] = 999
        original_scores[0] = 999
        
        # State should be unchanged
        self.assertEqual(state.pool[0], 1)
        self.assertEqual(state.bag[0], 5)
        self.assertEqual(state.scores[0], 10)

    def test_standard_scrabble_distribution_constant(self):
        """Test that the standard Scrabble distribution constant is correct"""
        # Check total tiles (should be 98 + 2 blanks = 100, but we're not including blanks)
        expected_total = 98  # Standard Scrabble without blanks
        actual_total = np.sum(STANDARD_SCRABBLE_DISTRIBUTION)
        self.assertEqual(actual_total, expected_total)
        
        # Check specific letter counts
        self.assertEqual(STANDARD_SCRABBLE_DISTRIBUTION[0], 9)   # A
        self.assertEqual(STANDARD_SCRABBLE_DISTRIBUTION[4], 12)  # E
        self.assertEqual(STANDARD_SCRABBLE_DISTRIBUTION[9], 1)   # J
        self.assertEqual(STANDARD_SCRABBLE_DISTRIBUTION[25], 1)  # Z

    def test_state_with_single_player(self):
        """Test creating a State with single player"""
        state = State(num_players=1)
        
        self.assertEqual(state.num_players, 1)
        self.assertEqual(len(state.words_per_player), 1)
        self.assertEqual(len(state.scores), 1)
        self.assertEqual(state.scores[0], 0)

    def test_state_with_many_players(self):
        """Test creating a State with many players"""
        num_players = 10
        state = State(num_players=num_players)
        
        self.assertEqual(state.num_players, num_players)
        self.assertEqual(len(state.words_per_player), num_players)
        self.assertEqual(len(state.scores), num_players)
        
        # All should be initialized properly
        for i in range(num_players):
            self.assertEqual(len(state.words_per_player[i]), 0)
            self.assertEqual(state.scores[i], 0)


class TestMakeWord(unittest.TestCase):
    """Test cases for the MakeWord class"""

    def test_move_creation_minimal(self):
        """Test creating a MakeWord with minimal parameters"""
        move = MakeWord(player=0, word="cat")
        
        self.assertEqual(move.player, 0)
        self.assertEqual(move.word, "cat")
        self.assertEqual(move.other_player_words, [])
        self.assertEqual(move.pool_letters, [])

    def test_move_creation_with_all_parameters(self):
        """Test creating a MakeWord with all parameters"""
        other_words = [(1, "dog"), (2, "bird")]
        pool_letters = ["a", "t"]
        
        move = MakeWord(
            player=0,
            word="cats",
            other_player_words=other_words,
            pool_letters=pool_letters
        )
        
        self.assertEqual(move.player, 0)
        self.assertEqual(move.word, "cats")
        self.assertEqual(move.other_player_words, [(1, "dog"), (2, "bird")])
        self.assertEqual(move.pool_letters, ["a", "t"])

    def test_move_word_case_conversion(self):
        """Test that word is converted to lowercase"""
        move = MakeWord(player=1, word="HELLO")
        self.assertEqual(move.word, "hello")
        
        move = MakeWord(player=1, word="MiXeD")
        self.assertEqual(move.word, "mixed")

    def test_move_creation_invalid_player_negative(self):
        """Test creating a MakeWord with negative player raises ValueError"""
        with self.assertRaises(ValueError) as context:
            MakeWord(player=-1, word="cat")
        self.assertIn("Player must be non-negative", str(context.exception))

    def test_move_creation_invalid_word_characters(self):
        """Test creating a MakeWord with invalid word characters raises ValueError"""
        with self.assertRaises(ValueError) as context:
            MakeWord(player=0, word="cat1")
        self.assertIn("invalid character: '1'", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            MakeWord(player=0, word="hello world")
        self.assertIn("invalid character: ' '", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            MakeWord(player=0, word="cat!")
        self.assertIn("invalid character: '!'", str(context.exception))

    def test_move_creation_empty_word(self):
        """Test creating a MakeWord with empty word is allowed"""
        move = MakeWord(player=0, word="")
        self.assertEqual(move.word, "")

    def test_move_with_other_player_words(self):
        """Test creating a MakeWord with words from other players"""
        other_words = [(1, "dog"), (2, "fish"), (0, "cat")]
        move = MakeWord(player=3, word="animals", other_player_words=other_words)
        
        self.assertEqual(move.player, 3)
        self.assertEqual(move.word, "animals")
        self.assertEqual(move.other_player_words, [(1, "dog"), (2, "fish"), (0, "cat")])
        self.assertEqual(move.pool_letters, [])

    def test_move_with_pool_letters(self):
        """Test creating a MakeWord with letters from pool"""
        pool_letters = ["a", "b", "c", "x", "y", "z"]
        move = MakeWord(player=1, word="cabxyz", pool_letters=pool_letters)
        
        self.assertEqual(move.player, 1)
        self.assertEqual(move.word, "cabxyz")
        self.assertEqual(move.other_player_words, [])
        self.assertEqual(move.pool_letters, ["a", "b", "c", "x", "y", "z"])

    def test_move_with_empty_lists(self):
        """Test creating a MakeWord with explicitly empty lists"""
        move = MakeWord(player=2, word="test", other_player_words=[], pool_letters=[])
        
        self.assertEqual(move.player, 2)
        self.assertEqual(move.word, "test")
        self.assertEqual(move.other_player_words, [])
        self.assertEqual(move.pool_letters, [])

    def test_move_complex_scenario(self):
        """Test a complex move scenario combining multiple elements"""
        other_words = [(0, "cat"), (1, "dog"), (2, "fish")]
        pool_letters = ["s", "e", "t"]
        
        move = MakeWord(
            player=3,
            word="catsdogsfishset",
            other_player_words=other_words,
            pool_letters=pool_letters
        )
        
        self.assertEqual(move.player, 3)
        self.assertEqual(move.word, "catsdogsfishset")
        self.assertEqual(len(move.other_player_words), 3)
        self.assertEqual(len(move.pool_letters), 3)

    def test_move_player_zero(self):
        """Test that player 0 is valid"""
        move = MakeWord(player=0, word="valid")
        self.assertEqual(move.player, 0)

    def test_move_large_player_number(self):
        """Test that large player numbers are valid"""
        move = MakeWord(player=999, word="valid")
        self.assertEqual(move.player, 999)

    def test_move_with_single_letter_word(self):
        """Test creating a MakeWord with single letter word"""
        move = MakeWord(player=1, word="a")
        self.assertEqual(move.word, "a")

    def test_move_with_long_word(self):
        """Test creating a MakeWord with very long word"""
        long_word = "supercalifragilisticexpialidocious"
        move = MakeWord(player=0, word=long_word)
        self.assertEqual(move.word, long_word)

    def test_move_other_player_words_types(self):
        """Test that other_player_words accepts various valid formats"""
        # Test with different player IDs and word types
        other_words = [(0, "a"), (999, "verylongword"), (1, "")]
        move = MakeWord(player=5, word="test", other_player_words=other_words)
        self.assertEqual(move.other_player_words, [(0, "a"), (999, "verylongword"), (1, "")])

    def test_move_pool_letters_types(self):
        """Test that pool_letters accepts various valid formats"""
        # Test with different letter combinations
        pool_letters = ["a", "z", "m", "q", "x"]
        move = MakeWord(player=0, word="test", pool_letters=pool_letters)
        self.assertEqual(move.pool_letters, ["a", "z", "m", "q", "x"])


class TestDrawLetters(unittest.TestCase):
    """Test cases for the DrawLetters class"""

    def test_draw_letters_creation_single_letter(self):
        """Test creating a DrawLetters with single letter"""
        move = DrawLetters(["a"])
        self.assertEqual(move.letters, ["a"])

    def test_draw_letters_creation_multiple_letters(self):
        """Test creating a DrawLetters with multiple letters"""
        move = DrawLetters(["a", "b", "c"])
        self.assertEqual(move.letters, ["a", "b", "c"])

    def test_draw_letters_creation_empty_list(self):
        """Test creating a DrawLetters with empty list"""
        move = DrawLetters([])
        self.assertEqual(move.letters, [])

    def test_draw_letters_case_conversion(self):
        """Test that DrawLetters converts letters to lowercase"""
        move = DrawLetters(["A", "B", "C"])
        self.assertEqual(move.letters, ["a", "b", "c"])

    def test_draw_letters_invalid_characters(self):
        """Test creating a DrawLetters with invalid characters raises ValueError"""
        with self.assertRaises(ValueError):
            DrawLetters(["1"])  # Number
        
        with self.assertRaises(ValueError):
            DrawLetters(["ab"])  # Multiple characters
        
        with self.assertRaises(ValueError):
            DrawLetters(["!"])  # Special character
        
        with self.assertRaises(ValueError):
            DrawLetters([" "])  # Space

    def test_draw_letters_mixed_case(self):
        """Test DrawLetters with mixed case letters"""
        move = DrawLetters(["A", "z", "M"])
        self.assertEqual(move.letters, ["a", "z", "m"])

    def test_draw_letters_all_alphabet(self):
        """Test DrawLetters with all alphabet letters"""
        letters = [chr(ord('a') + i) for i in range(26)]
        move = DrawLetters(letters)
        self.assertEqual(move.letters, letters)


if __name__ == '__main__':
    unittest.main()