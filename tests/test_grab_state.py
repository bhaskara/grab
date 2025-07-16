"""
Unit tests for grab_state module
"""

import unittest
import numpy as np
from src.grab.grab_state import Word


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


if __name__ == '__main__':
    unittest.main()