"""
Unit tests for word list functionality
"""

import unittest
import tempfile
import os
from unittest.mock import patch
from src.grab.grab_game import load_word_list


class TestWordList(unittest.TestCase):
    """Test cases for word list loading functionality"""

    def test_load_word_list_valid_dictionary(self):
        """Test loading a valid dictionary file"""
        # Create a temporary dictionary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("APPLE\nBANANA\nCHERRY\n\nDUCK\n")
            temp_file = f.name
        
        try:
            # Mock the file path resolution to use our temp file
            with patch('os.path.join') as mock_join:
                mock_join.return_value = temp_file
                with patch('os.path.exists', return_value=True):
                    words = load_word_list('twl06')
                    
                    expected_words = {'apple', 'banana', 'cherry', 'duck'}
                    self.assertEqual(words, expected_words)
                    self.assertIsInstance(words, set)
        finally:
            # Clean up temp file
            os.unlink(temp_file)

    def test_load_word_list_invalid_dictionary(self):
        """Test loading an invalid dictionary name"""
        with self.assertRaises(ValueError) as context:
            load_word_list('invalid_dict')
        
        self.assertIn("Unknown dictionary name", str(context.exception))

    def test_load_word_list_file_not_found(self):
        """Test loading a dictionary file that doesn't exist"""
        with patch('os.path.exists', return_value=False):
            with self.assertRaises(FileNotFoundError) as context:
                load_word_list('twl06')
            
            self.assertIn("Dictionary file not found", str(context.exception))

    def test_load_word_list_empty_lines_ignored(self):
        """Test that empty lines in dictionary files are ignored"""
        # Create a temporary dictionary file with empty lines
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("WORD1\n\n\nWORD2\n   \nWORD3\n")
            temp_file = f.name
        
        try:
            with patch('os.path.join') as mock_join:
                mock_join.return_value = temp_file
                with patch('os.path.exists', return_value=True):
                    words = load_word_list('sowpods')
                    
                    expected_words = {'word1', 'word2', 'word3'}
                    self.assertEqual(words, expected_words)
        finally:
            os.unlink(temp_file)


if __name__ == '__main__':
    unittest.main()