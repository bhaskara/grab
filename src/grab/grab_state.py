"""Contains basic data structures that represent the Grab game state and moves

The actual game logic is contained in grab_game.py.

"""
from dataclasses import dataclass
from typing import List, Set, Optional, Tuple
import numpy as np


class NoWordFoundException(Exception):
    """Exception raised when construct_move cannot find a valid word combination.
    
    Attributes
    ----------
    word : str
        The word that could not be constructed
    state : State
        The game state when the attempt was made
    """
    
    def __init__(self, word: str, state: 'State'):
        """Initialize the exception.
        
        Parameters
        ----------
        word : str
            The word that could not be constructed
        state : State
            The game state when the attempt was made
        """
        self.word = word
        self.state = state
        message = f"Cannot construct word '{word}' with available letters and words"
        super().__init__(message)


# Standard Scrabble letter distribution
STANDARD_SCRABBLE_DISTRIBUTION = np.array([
    9,  # A
    2,  # B
    2,  # C
    4,  # D
    12, # E
    2,  # F
    3,  # G
    2,  # H
    9,  # I
    1,  # J
    1,  # K
    4,  # L
    2,  # M
    6,  # N
    8,  # O
    2,  # P
    1,  # Q
    6,  # R
    4,  # S
    6,  # T
    4,  # U
    2,  # V
    2,  # W
    1,  # X
    2,  # Y
    1   # Z
], dtype=int)


@dataclass
class State(object):
    """Dataclass that contains the state of the grab game.

    Attributes
    ----------
    num_players : int
        Number of players in the game
    words_per_player : List[List[Word]]
        The ith element is the list of words that the ith player currently has
        in front of them
    pool : np.ndarray
        Array of 26 integers representing the letters in the central pool, using the same 
        method as the letter_counts attribute of the Word class
    bag : np.ndarray
        Array of 26 integers representing the letters remaining in the bag, using the same 
        method as the letter_counts attribute of the Word class
    scores : List[int]
        Scores per player, where scores[i] is the score for player i

    """
    num_players: int
    words_per_player: List[List['Word']]
    pool: np.ndarray
    bag: np.ndarray
    scores: List[int]
    
    def __init__(self, num_players: int, 
                 words_per_player: Optional[List[List['Word']]] = None,
                 pool: Optional[np.ndarray] = None,
                 bag: Optional[np.ndarray] = None,
                 scores: Optional[List[int]] = None):
        """Initialize a new game state.

        Parameters
        ----------
        num_players : int
            Number of players in the game
        words_per_player : List[List[Word]], optional
            Initial words for each player. If None, creates empty lists for all players.
        pool : np.ndarray, optional
            Initial letters in the central pool. If None, creates empty pool.
            Must be array of 26 integers representing letter counts.
        bag : np.ndarray, optional
            Initial letter distribution in the bag. If None, uses standard Scrabble 
            distribution. Must be array of 26 integers representing letter counts.
        scores : List[int], optional
            Initial scores for each player. If None, creates zero scores for all players.

        Raises
        ------
        ValueError
            If num_players is less than 1, if arrays have wrong shape, or if list 
            lengths don't match num_players

        """
        if num_players < 1:
            raise ValueError("Number of players must be at least 1")
            
        self.num_players = num_players
        
        if words_per_player is None:
            self.words_per_player = [[] for _ in range(num_players)]
        else:
            if len(words_per_player) != num_players:
                raise ValueError(f"words_per_player must have length {num_players}, got {len(words_per_player)}")
            self.words_per_player = words_per_player
        
        if pool is None:
            self.pool = np.zeros(26, dtype=int)
        else:
            if pool.shape != (26,):
                raise ValueError("pool must be an array of 26 integers")
            self.pool = pool.copy()
        
        if scores is None:
            self.scores = [0] * num_players
        else:
            if len(scores) != num_players:
                raise ValueError(f"scores must have length {num_players}, got {len(scores)}")
            self.scores = scores.copy()
        
        if bag is None:
            self.bag = STANDARD_SCRABBLE_DISTRIBUTION.copy()
        else:
            if bag.shape != (26,):
                raise ValueError("bag must be an array of 26 integers")
            self.bag = bag.copy()
    

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



@dataclass
class Move(object):
    """Represents a single move made by a player forming a new word

    Attributes
    ----------
    player : int
        Which player is making this move (0-indexed)
    word : str
        The word being made
    other_player_words : List[Tuple[int, str]]
        Each element contains another player ID and a word currently
        in front of that player that will be used in this move
    pool_letters : List[str]
        List of letters being used from the central pool

    """
    player: int
    word: str
    other_player_words: List[Tuple[int, str]]
    pool_letters: List[str]
    
    def __init__(self, player: int, word: str, 
                 other_player_words: Optional[List[Tuple[int, str]]] = None,
                 pool_letters: Optional[List[str]] = None):
        """Initialize a new move.

        Parameters
        ----------
        player : int
            Which player is making this move (0-indexed)
        word : str
            The word being made. Must contain only letters 'a' to 'z'
        other_player_words : List[Tuple[int, str]], optional
            List of (player_id, word) tuples for words taken from other players.
            If None, defaults to empty list.
        pool_letters : List[str], optional
            List of letters being used from the central pool.
            If None, defaults to empty list.

        Raises
        ------
        ValueError
            If player is negative or if word contains invalid characters

        """
        if player < 0:
            raise ValueError("Player must be non-negative")
        
        # Validate word
        word_lower = word.lower()
        for char in word_lower:
            if not ('a' <= char <= 'z'):
                raise ValueError(f"Word contains invalid character: '{char}'. Only letters 'a' to 'z' are allowed.")
        
        self.player = player
        self.word = word_lower
        
        # Handle other_player_words
        if other_player_words is None:
            self.other_player_words = []
        else:
            self.other_player_words = other_player_words
        
        # Handle pool_letters
        if pool_letters is None:
            self.pool_letters = []
        else:
            self.pool_letters = pool_letters


