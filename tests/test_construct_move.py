#!/usr/bin/env python3
"""Test script to verify construct_move function works correctly."""

import pytest
import numpy as np
from src.grab.grab_state import State, Word
from src.grab.grab_game import Grab, NoWordFoundException, DisallowedWordException

def test_construct_move_from_pool_only():
    """Test making a word using only pool letters."""
    game = Grab()
    state = State(num_players=2)
    
    # Add letters to pool: 'cat'
    state.pool[0] = 1  # 'a'
    state.pool[2] = 1  # 'c'
    state.pool[19] = 1  # 't'
    
    move, new_state = game.construct_move(state, 0, "cat")
    
    assert move.player == 0
    assert move.word == "cat"
    assert move.other_player_words == []
    assert set(move.pool_letters) == {'c', 'a', 't'}
    
    # Check new state
    assert new_state.num_players == 2
    assert len(new_state.words_per_player[0]) == 1
    assert new_state.words_per_player[0][0].word == "cat"
    assert new_state.scores[0] == 5  # Scrabble score: c(3) + a(1) + t(1) = 5
    assert new_state.pool[0] == 0  # 'a' used
    assert new_state.pool[2] == 0  # 'c' used
    assert new_state.pool[19] == 0  # 't' used

def test_construct_move_with_existing_word():
    """Test making a word using existing word plus pool letters."""
    game = Grab(disallow_common_suffixes=False)  # Disable suffix checking for this test
    state = State(num_players=2)
    
    # Add existing word to player 0
    state.words_per_player[0].append(Word("cat"))
    
    # Add 's' to pool
    state.pool[18] = 1  # 's'
    
    move, new_state = game.construct_move(state, 1, "cats")
    
    assert move.player == 1
    assert move.word == "cats"
    assert move.other_player_words == [(0, "cat")]
    assert move.pool_letters == ['s']
    
    # Check new state
    assert len(new_state.words_per_player[0]) == 0  # "cat" was used
    assert len(new_state.words_per_player[1]) == 1  # "cats" was added
    assert new_state.words_per_player[1][0].word == "cats"
    assert new_state.scores[1] == 6  # Scrabble score: c(3) + a(1) + t(1) + s(1) = 6
    assert new_state.pool[18] == 0  # 's' used

def test_construct_move_impossible_word():
    """Test that impossible words raise NoWordFoundException."""
    game = Grab()
    state = State(num_players=2)
    
    # Empty pool, try to make a valid word that can't be constructed
    with pytest.raises(NoWordFoundException, match="Cannot construct word 'cat'"):
        game.construct_move(state, 0, "cat")

def test_construct_move_invalid_player():
    """Test that invalid player raises ValueError."""
    game = Grab()
    state = State(num_players=2)
    
    with pytest.raises(ValueError, match="Player 5 is out of range"):
        game.construct_move(state, 5, "cat")

def test_construct_move_invalid_word():
    """Test that invalid word raises DisallowedWordException."""
    game = Grab()
    state = State(num_players=2)
    
    with pytest.raises(DisallowedWordException, match="Word 'cat1' is not in the allowed word list"):
        game.construct_move(state, 0, "cat1")

def test_construct_move_anagram_rejection():
    """Test that stealing a word to make an anagram (same length) is rejected.

    For example, stealing "cat" to make "act" should fail because the new word
    is not strictly longer than the stolen word.
    """
    game = Grab()
    state = State(num_players=2)

    # Give player 0 the word "cat"
    state.words_per_player[0].append(Word("cat"))

    # Add letters to pool that would allow "act" from pool alone too
    # but we want to test that stealing "cat" to rearrange as "act" fails
    # Don't put a/c/t in pool so the only way to make "act" is by stealing "cat"

    with pytest.raises(NoWordFoundException, match="Cannot construct word 'act'"):
        game.construct_move(state, 1, "act")


def test_construct_move_same_length_steal_rejection():
    """Test that stealing a word to make a same-length word is rejected.

    Even if extra pool letters are available, if the resulting word is the
    same length as the stolen word, the move should be rejected.
    """
    game = Grab()
    state = State(num_players=2)

    # Give player 0 the word "cat"
    state.words_per_player[0].append(Word("cat"))

    # Add 't', 'a', 'c' to pool (extras beyond what "cat" provides)
    state.pool[0] = 1   # 'a'
    state.pool[2] = 1   # 'c'
    state.pool[19] = 1  # 't'

    # "tac" is same length as "cat" — should fail to steal
    # (but could succeed from pool alone if "tac" were a valid word)
    # Since "tac" isn't a real word, use "act" which is valid
    # "act" can be made from pool letters alone (no steal), so it should succeed
    move, new_state = game.construct_move(state, 1, "act")
    # Verify it was made from pool, not by stealing
    assert move.other_player_words == []
    assert len(new_state.words_per_player[0]) == 1  # player 0 still has "cat"


def test_construct_move_longer_steal_succeeds():
    """Test that stealing a word to make a strictly longer word succeeds.

    Stealing "cat" to make "cats" (longer) should work fine.
    """
    game = Grab(disallow_common_suffixes=False)
    state = State(num_players=2)

    # Give player 0 the word "cat"
    state.words_per_player[0].append(Word("cat"))

    # Add 's' to pool
    state.pool[18] = 1  # 's'

    move, new_state = game.construct_move(state, 1, "cats")

    assert move.other_player_words == [(0, "cat")]
    assert move.word == "cats"
    assert len(new_state.words_per_player[0]) == 0  # "cat" was stolen
    assert new_state.words_per_player[1][0].word == "cats"


def test_construct_move_pool_only_unaffected_by_length_check():
    """Test that making a word purely from pool letters is unaffected.

    The length check only applies when stealing an existing word. Making a
    short word from pool letters should still work.
    """
    game = Grab()
    state = State(num_players=2)

    # Add letters for "at" to pool
    state.pool[0] = 1   # 'a'
    state.pool[19] = 1  # 't'

    move, new_state = game.construct_move(state, 0, "at")

    assert move.other_player_words == []
    assert move.word == "at"
    assert set(move.pool_letters) == {'a', 't'}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])