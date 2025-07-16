"""Contains basic data structures that represent the Grab game state and moves

"""
from dataclasses import dataclass
import numpy as np

@dataclass
class Word(object):
    """Dataclass that wraps a single word with an array representing
    counts of letters, which is used for efficiently determining whether
    moves are legal, and how a word can be formed from other words.

    The fields are:
    - word: string containing the actual word, e.g., "moon"
    - letter_counts: Numpy array of integers, where the i^th position
      contains the number of occurrences of the i^th letter (where the 0th
      letter is a, and the 25th letter is z).  So if the word was "moon", this
      array would have a 1 at positions 12 and 13 (m and n), a 2 at position
      14 (o), and 0 elsewhere.

    """
    word: str
    letter_counts: np.ndarray
    
    def __init__(self, word: str):
        """Only takes in the word, automatically computes the counts.

        Parameters
        ----------
        word : str
            The word string to create the Word object from

        Raises
        ------
        ValueError
            If the word contains any characters that are not letters from 'a' to 'z'

        """
        self.word = word.lower()
        self.letter_counts = np.zeros(26, dtype=int)
        
        for char in self.word:
            if not ('a' <= char <= 'z'):
                raise ValueError(f"Word contains invalid character: '{char}'. Only letters 'a' to 'z' are allowed.")
            self.letter_counts[ord(char) - ord('a')] += 1
