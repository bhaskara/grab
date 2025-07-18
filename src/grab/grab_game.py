from typing import Set
import os
import numpy as np
from .grab_state import State, Word, Move, NoWordFoundException

# Standard Scrabble letter scores (A=1, B=3, C=3, ...)
SCRABBLE_LETTER_SCORES = np.array([
    1, 3, 3, 2, 1, 4, 2, 4, 1, 8, 5, 1, 3, 1, 1, 3, 10, 1, 1, 1, 1, 4, 4, 8, 4, 10
])


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

    
    def construct_move(self, state: State, player: int, word: str) -> tuple[Move, State]:
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
        move : Move
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
        # Algorithm overview
        # 0. First construct a letter counts array for the central pool similar to the
        #    one stored per word, and another for the new word.
        # 1. Construct a list existing_words_to_use, where each entry is a *set*
        #    of existing words to be use.  For now this list only includes sets of
        #    zero or one existing word, and is in increasing order of set size.
        # 2. For each entry of this list, figure out the remaining letter counts if these
        #    words were used.  This can be done efficiently by subtracting letter counts.
        #    If the result of the subtraction has any negative entries, go to next iteration
        # 3. Otherwise (if the remaining letter counts are nonnegative), check if they can
        #    be all obtained from the pool, by checking if remaining_counts <= pool_counts.
        # 4. If yes, construct and return the Move and State.  If not, go back to 2)
        #    for the next iteration.
        # 5. If the loop terminates, the word cannot be made.
        
        # Input validation
        if player < 0 or player >= state.num_players:
            raise ValueError(f"Player {player} is out of range (0-{state.num_players-1})")
        
        # Step 0: Construct letter counts for the new word
        try:
            target_word = Word(word)
        except ValueError as e:
            raise ValueError(f"Invalid word '{word}': {e}")
        
        target_counts = target_word.letter_counts
        pool_counts = state.pool
        
        # Step 1: Construct list of existing words to use (sets of 0 or 1 word)
        existing_words_to_use = []
        
        # First try with no existing words (empty set)
        existing_words_to_use.append([])
        
        # Then try with each individual existing word from all players
        for p in range(state.num_players):
            for word_obj in state.words_per_player[p]:
                existing_words_to_use.append([(p, word_obj)])
        
        # Step 2-4: Try each combination
        for word_set in existing_words_to_use:
            # Calculate remaining letter counts after using these words
            remaining_counts = target_counts.copy()
            other_player_words = []
            
            for p, word_obj in word_set:
                remaining_counts -= word_obj.letter_counts
                other_player_words.append((p, word_obj.word))
            
            # Check if remaining counts are non-negative
            if np.any(remaining_counts < 0):
                continue
            
            # Step 3: Check if remaining letters can be obtained from pool
            if np.all(remaining_counts <= pool_counts):
                # Step 4: Construct the Move
                pool_letters = []
                for letter_idx in range(26):
                    letter_char = chr(ord('a') + letter_idx)
                    for _ in range(remaining_counts[letter_idx]):
                        pool_letters.append(letter_char)
                
                move = Move(
                    player=player,
                    word=word,
                    other_player_words=other_player_words,
                    pool_letters=pool_letters
                )
                
                # Construct the new state after applying this move
                new_state = State(
                    num_players=state.num_players,
                    words_per_player=[words[:] for words in state.words_per_player],  # Deep copy
                    pool=state.pool.copy(),
                    bag=state.bag.copy(),
                    scores=state.scores.copy()
                )
                
                # Remove used words from their original players
                for p, word_str in other_player_words:
                    # Find and remove the word from player p's word list
                    for i, word_obj in enumerate(new_state.words_per_player[p]):
                        if word_obj.word == word_str:
                            new_state.words_per_player[p].pop(i)
                            break
                
                # Remove used letters from the pool
                for letter_idx in range(26):
                    new_state.pool[letter_idx] -= remaining_counts[letter_idx]
                
                # Add the new word to the current player's word list
                new_state.words_per_player[player].append(Word(word))
                
                # Update the current player's score (sum of letter values in the new word)
                word_score = np.dot(target_word.letter_counts, self.letter_scores)
                new_state.scores[player] += word_score
                
                return move, new_state
        
        # Step 5: If we get here, the word cannot be made
        raise NoWordFoundException(word, state)



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
    
