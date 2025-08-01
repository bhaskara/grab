from typing import Set, Union, Optional, Tuple
import os
import numpy as np
from .grab_state import State, Word, MakeWord, DrawLetters, Move


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


class DisallowedWordException(Exception):
    """Exception raised when a word is not in the allowed word list.
    
    Attributes
    ----------
    word : str
        The word that is not allowed
    """
    
    def __init__(self, word: str):
        """Initialize the exception.
        
        Parameters
        ----------
        word : str
            The word that is not allowed
        """
        self.word = word
        message = f"Word '{word}' is not in the allowed word list"
        super().__init__(message)


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
    num_players : int, optional
        Number of players in the game. Defaults to 2.
    word_list : str, optional
        Designates the list of allowed words.  Either 'twl06' or 'sowpods'.
        Defaults to 'twl06'.
    letter_scores : np.ndarray, optional
        Length-26 array containing per-letter scores (a=0, b=1, ..., z=25).
        Defaults to standard Scrabble letter scores.
    
    """

    def __init__(self, num_players: int = 2, word_list: str = 'twl06', letter_scores: np.ndarray = None, next_letters: Optional[list] = None):
        """Initialize a Grab game instance.
        
        Parameters
        ----------
        num_players : int, optional
            Number of players in the game. Defaults to 2.
        word_list : str, optional
            Designates the list of allowed words.  Either 'twl06' or 'sowpods'.
            Defaults to 'twl06'.
        letter_scores : np.ndarray, optional
            Length-26 array containing per-letter scores (a=0, b=1, ..., z=25).
            Defaults to standard Scrabble letter scores.
        next_letters : List[str], optional
            Initial list of letters to be drawn in order before falling back to random 
            sampling. If None, creates empty list.
        """
        if num_players < 1:
            raise ValueError("Number of players must be at least 1")
        
        if letter_scores is None:
            self.letter_scores = SCRABBLE_LETTER_SCORES.copy()
        else:
            if len(letter_scores) != 26:
                raise ValueError("letter_scores must be a length-26 array")
            self.letter_scores = np.array(letter_scores)
        
        self.valid_words = load_word_list(word_list)
        
        # Initialize the game state to the starting state
        self._state = State(num_players=num_players, next_letters=next_letters)

    @property
    def state(self) -> State:
        """Get the current game state.
        
        Returns
        -------
        State
            The current game state
        """
        return self._state
    
    @state.setter
    def state(self, new_state: State) -> None:
        """Set the current game state.
        
        Parameters
        ----------
        new_state : State
            The new game state to set
        
        Raises
        ------
        TypeError
            If new_state is not a State instance
        """
        if not isinstance(new_state, State):
            raise TypeError("state must be a State instance")
        self._state = new_state

    def handle_action(self, player: int, action: Union[str, int]) -> Tuple[State, Optional[Move]]:
        """Handle an action by a player in the current state.

        An action is either playing a new word or passing.

        Parameters
        ----------
        player: int
            The id of the player doing this action.
        action: str or int
            This is either a string representing a word, or the integer 0 representing
            passing. In the former case, attempt to make the word using construct_word.
            If it's 0, update the state to mark that player as passed.  If all players
            have passed, then either draw a new letter (if there are any left in the
            bag) or end the game (if not).

        Returns
        -------
        new_state: State
            The state after making this move
        move: Move, optional
            Assuming the player action resulted in a new word, drawing letters, or
            ending the game, return the Move object.  Else return None.

        Raises
        ------
        ValueError
            If player is out of range or action is invalid
        DisallowedWordException
            If the word is not in the allowed word list
        NoWordFoundException
            If the word cannot be constructed with available letters

        """
        current_state = self._state
        
        # Validate player
        if player < 0 or player >= current_state.num_players:
            raise ValueError(f"Player {player} is out of range (0-{current_state.num_players-1})")
        
        # Handle word action (string)
        if isinstance(action, str):
            # Attempt to make the word using construct_move
            move, new_state = self.construct_move(current_state, player, action)
            # Update the internal state
            self._state = new_state
            return new_state, move
        
        # Handle pass action (integer 0)
        elif action == 0:
            # Create new state with player marked as passed
            new_state = State(
                num_players=current_state.num_players,
                words_per_player=[words[:] for words in current_state.words_per_player],
                pool=current_state.pool.copy(),
                bag=current_state.bag.copy(),
                scores=current_state.scores.copy(),
                passed=current_state.passed.copy()
            )
            
            # Mark this player as passed
            new_state.passed[player] = True
            
            # Check if all players have passed
            if all(new_state.passed):
                # All players have passed - either draw letter or end game
                total_letters_in_bag = np.sum(new_state.bag)
                
                if total_letters_in_bag > 0:
                    # Draw a letter (this resets all passed status to False)
                    draw_move, final_state = self.construct_draw_letters(new_state, 1)
                    self._state = final_state
                    return final_state, draw_move
                else:
                    # No letters left - end the game
                    final_state = self.end_game(new_state)
                    self._state = final_state
                    return final_state, None  # end_game doesn't return a Move
            else:
                # Not all players have passed - just update state
                self._state = new_state
                return new_state, None  # No move for simple pass
        
        # Invalid action
        else:
            raise ValueError(f"Invalid action: {action}. Action must be a string (word) or integer 0 (pass).")
        

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
        DisallowedWordException
            If the word is not in the allowed word list
        NoWordFoundException
            If the word could not be made given the current board state
        ValueError
            If the player is out of range or the word contains invalid characters

        """
        # Input validation
        if player < 0 or player >= state.num_players:
            raise ValueError(f"Player {player} is out of range (0-{state.num_players-1})")
        
        # Check if word is in valid word list
        if word.lower() not in self.valid_words:
            raise DisallowedWordException(word)
        
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
                    scores=state.scores.copy(),
                    passed=state.passed.copy()
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


    def end_game(self, state: State) -> State:
        """Return the state after ending the game.

        When we end the game, each player's score is increased by the scores of the
        words currently in front of them.

        Parameters
        ----------
        state : State
            The current game state

        Returns
        -------
        State
            The final game state with bonus scores added
        """
        # Create a new state as a copy of the current state
        end_state = State(
            num_players=state.num_players,
            words_per_player=[words[:] for words in state.words_per_player],  # Deep copy
            pool=state.pool.copy(),
            bag=state.bag.copy(),
            scores=state.scores.copy(),
            passed=state.passed.copy()
        )
        
        # Add bonus scores for each player based on their remaining words
        for player in range(state.num_players):
            bonus_score = 0
            for word in state.words_per_player[player]:
                # Calculate the score for this word using letter scores
                word_score = np.dot(word.letter_counts, self.letter_scores)
                bonus_score += word_score
            
            # Add the bonus to the player's score
            end_state.scores[player] += bonus_score
        
        return end_state
    

    def construct_draw_letters(self, state: State, num_letters: int = 1) -> tuple[DrawLetters, State]:
        """Construct a DrawLetters move that draws letters from the bag to the pool.
        
        Uses next_letters list first, then falls back to random sampling.

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
            If num_letters is not positive, if there aren't enough letters in the bag,
            or if next_letters contains letters not available in the bag

        """
        if num_letters <= 0:
            raise ValueError("Number of letters to draw must be positive")
        
        # Check if there are enough letters in the bag
        total_letters_in_bag = np.sum(state.bag)
        if total_letters_in_bag < num_letters:
            raise ValueError(f"Not enough letters in bag. Requested {num_letters}, but only {total_letters_in_bag} available")
        
        drawn_letters = []
        remaining_next_letters = state.next_letters.copy()
        bag_copy = state.bag.copy()
        
        # First, try to draw from next_letters
        for _ in range(num_letters):
            if remaining_next_letters:
                # Pop the next letter from the list
                letter = remaining_next_letters.pop(0)
                letter_idx = ord(letter) - ord('a')
                
                # Check if this letter is available in the bag
                if bag_copy[letter_idx] <= 0:
                    raise ValueError(f"Letter '{letter}' from next_letters is not available in the bag")
                
                drawn_letters.append(letter)
                bag_copy[letter_idx] -= 1
            else:
                # Fall back to random sampling
                available_letters = []
                for letter_idx in range(26):
                    letter_char = chr(ord('a') + letter_idx)
                    count = bag_copy[letter_idx]
                    available_letters.extend([letter_char] * count)
                
                if not available_letters:
                    raise ValueError("No more letters available in bag for random sampling")
                
                import random
                letter = random.choice(available_letters)
                drawn_letters.append(letter)
                letter_idx = ord(letter) - ord('a')
                bag_copy[letter_idx] -= 1
        
        # Create the DrawLetters move
        move = DrawLetters(drawn_letters)
        
        # Construct the new state after applying this move
        new_state = State(
            num_players=state.num_players,
            words_per_player=[words[:] for words in state.words_per_player],  # Deep copy
            pool=state.pool.copy(),
            bag=bag_copy,
            scores=state.scores.copy(),
            passed=[False] * state.num_players,
            next_letters=remaining_next_letters
        )
        
        # Add drawn letters to the pool (bag already updated in bag_copy)
        for letter in drawn_letters:
            letter_idx = ord(letter) - ord('a')
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
    
