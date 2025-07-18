from typing import Set
import os
import numpy as np
from .grab_state import State, Word, MakeWord, DrawLetters, NoWordFoundException

# Standard Scrabble letter scores (A=1, B=3, C=3, ...)
SCRABBLE_LETTER_SCORES = np.array([
    1, 3, 3, 2, 1, 4, 2, 4, 1, 8, 5, 1, 3, 1, 1, 3, 10, 1, 1, 1, 1, 4, 4, 8, 4, 10
])

# Pre-computed character array for performance
LETTERS = [chr(ord('a') + i) for i in range(26)]


class Grab(object):
    """This class implements the logic of the grab game.

    Parameters
    ----------
    letter_scores : np.ndarray, optional
        Length-26 array containing per-letter scores (a=0, b=1, ..., z=25).
        Defaults to standard Scrabble letter scores.
    """

    def __init__(self, letter_scores: np.ndarray = None):
        """Initialize a Grab game instance.
        
        Parameters
        ----------
        letter_scores : np.ndarray, optional
            Length-26 array containing per-letter scores (a=0, b=1, ..., z=25).
            Defaults to standard Scrabble letter scores.
        """
        if letter_scores is None:
            self.letter_scores = SCRABBLE_LETTER_SCORES.copy()
        else:
            if len(letter_scores) != 26:
                raise ValueError("letter_scores must be a length-26 array")
            self.letter_scores = np.array(letter_scores)

    
    def construct_move(self, state: State, player: int, word: str) -> tuple[MakeWord, State]:
        """Construct a Move that enables a player to make a particular word.

        Specifically, this figures out which combination of existing player words
        together with letters in the pool can be combined to make the new word.  In
        the rare case that there are multiple ways to construct the word, it returns an
        arbitrary one of those.

        For now the algorithm only allows using at most *one* existing player word.

        Parameters
        ----------
        state : State
            The state from which to make this word
        player : int
            The player who wants to make the word
        word : str
            The new word being made.

        Returns
        -------
        move : MakeWord
            A legal move corresponding to the creation of the given word by this player
        new_state : State
            The resulting state after making this move

        Raises
        ------
        NoWordFoundException
            If the word could not be made given the current board state
        ValueError
            If the player is out of range or the word contains invalid characters

        """
        # Input validation
        if player < 0 or player >= state.num_players:
            raise ValueError(f"Player {player} is out of range (0-{state.num_players-1})")
        
        # Construct letter counts for the new word
        try:
            target_word = Word(word)
        except ValueError as e:
            raise ValueError(f"Invalid word '{word}': {e}")
        
        target_counts = target_word.letter_counts
        pool_counts = state.pool
        
        # Early feasibility check: quick rejection if impossible
        total_available = pool_counts.copy()
        for p in range(state.num_players):
            for word_obj in state.words_per_player[p]:
                total_available += word_obj.letter_counts
        
        if np.any(target_counts > total_available):
            raise NoWordFoundException(word, state)
        
        # Build list of word options with indices for O(1) removal later
        # Each entry is (player_idx, word_idx, word_obj)
        existing_word_options = []
        
        # First option: no existing words
        existing_word_options.append([])
        
        # Then each individual existing word from all players
        for p in range(state.num_players):
            for w_idx, word_obj in enumerate(state.words_per_player[p]):
                existing_word_options.append([(p, w_idx, word_obj)])
        
        # Try each combination
        for word_set in existing_word_options:
            # Calculate remaining letter counts after using these words
            remaining_counts = target_counts.copy()
            used_word_indices = []  # Store (player_idx, word_idx) for efficient removal
            other_player_words = []  # For the MakeWord object
            
            for p, w_idx, word_obj in word_set:
                remaining_counts -= word_obj.letter_counts
                used_word_indices.append((p, w_idx))
                other_player_words.append((p, word_obj.word))
            
            # Check if remaining counts are non-negative
            if np.any(remaining_counts < 0):
                continue
            
            # Check if remaining letters can be obtained from pool
            if np.all(remaining_counts <= pool_counts):
                # Found a valid combination - now construct move and state
                
                # Build pool_letters list efficiently
                pool_letters = []
                for letter_idx in range(26):
                    count = remaining_counts[letter_idx]
                    if count > 0:
                        pool_letters.extend([LETTERS[letter_idx]] * count)
                
                move = MakeWord(
                    player=player,
                    word=word,
                    other_player_words=other_player_words,
                    pool_letters=pool_letters
                )
                
                # Lazy state creation - only create after confirming valid move
                new_state = State(
                    num_players=state.num_players,
                    words_per_player=[words[:] for words in state.words_per_player],  # Deep copy
                    pool=pool_counts - remaining_counts,  # Efficient pool update
                    bag=state.bag.copy(),
                    scores=state.scores.copy()
                )
                
                # Remove used words efficiently using stored indices (in reverse order)
                for p, w_idx in sorted(used_word_indices, key=lambda x: x[1], reverse=True):
                    new_state.words_per_player[p].pop(w_idx)
                
                # Add the new word to the current player's word list (reuse target_word)
                new_state.words_per_player[player].append(target_word)
                
                # Update the current player's score
                word_score = np.dot(target_word.letter_counts, self.letter_scores)
                new_state.scores[player] += word_score
                
                return move, new_state
        
        # If we get here, the word cannot be made
        raise NoWordFoundException(word, state)

    def construct_draw_letters(self, state: State, num_letters: int = 1) -> tuple[DrawLetters, State]:
        """Construct a DrawLetters move that draws random letters from the bag to the pool.

        Parameters
        ----------
        state : State
            The current game state
        num_letters : int, optional
            Number of letters to draw from the bag. Defaults to 1.

        Returns
        -------
        move : DrawLetters
            A DrawLetters move containing the specific letters drawn
        new_state : State
            The resulting state after drawing the letters

        Raises
        ------
        ValueError
            If num_letters is not positive or if there aren't enough letters in the bag

        """
        if num_letters <= 0:
            raise ValueError("Number of letters to draw must be positive")
        
        # Check if there are enough letters in the bag
        total_letters_in_bag = np.sum(state.bag)
        if total_letters_in_bag < num_letters:
            raise ValueError(f"Not enough letters in bag. Requested {num_letters}, but only {total_letters_in_bag} available")
        
        # Create a list of available letters based on bag contents
        available_letters = []
        for letter_idx in range(26):
            letter_char = chr(ord('a') + letter_idx)
            count = state.bag[letter_idx]
            available_letters.extend([letter_char] * count)
        
        # Randomly select letters from the bag
        import random
        drawn_letters = random.sample(available_letters, num_letters)
        
        # Create the DrawLetters move
        move = DrawLetters(drawn_letters)
        
        # Construct the new state after applying this move
        new_state = State(
            num_players=state.num_players,
            words_per_player=[words[:] for words in state.words_per_player],  # Deep copy
            pool=state.pool.copy(),
            bag=state.bag.copy(),
            scores=state.scores.copy()
        )
        
        # Remove drawn letters from the bag and add them to the pool
        for letter in drawn_letters:
            letter_idx = ord(letter) - ord('a')
            new_state.bag[letter_idx] -= 1
            new_state.pool[letter_idx] += 1
        
        return move, new_state



def load_word_list(dict_name : str) -> Set[str]:
    """Loads a word list into a set of strings

    dict_name can be one of 'twl06' or 'sowpods'

    """
    # The word lists are in the data/ subdirectory of the repo root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(script_dir))
    data_dir = os.path.join(repo_root, 'data')
    
    if dict_name not in ['twl06', 'sowpods']:
        raise ValueError(f"Unknown dictionary name: {dict_name}. Must be 'twl06' or 'sowpods'")
    
    dict_file = os.path.join(data_dir, f'{dict_name}.txt')
    
    if not os.path.exists(dict_file):
        raise FileNotFoundError(f"Dictionary file not found: {dict_file}")
    
    words = set()
    with open(dict_file, 'r', encoding='utf-8') as f:
        for line in f:
            word = line.strip().lower()
            if word:  # Skip empty lines
                words.add(word)
    
    return words
    
