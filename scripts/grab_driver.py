#!/usr/bin/env python3
"""
Interactive driver script for the Grab word game.

This script allows playing Grab from the command line with multiple players.
Commands:
- "PLAYER_NUM WORD" - Player attempts to make a word (e.g., "1 cat")
- "PLAYER_NUM" - Player passes
- "draw" - Draw next letter from bag to pool
- "end" - End the game and show final scores
- "help" - Show this help message
- "quit" - Exit without ending game

Usage: python grab_driver.py NUM_PLAYERS
"""

import sys
import os
import argparse
import numpy as np
from typing import List

# Add the src directory to Python path so we can import grab modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from grab.grab_game import Grab, NoWordFoundException, DisallowedWordException
from grab.grab_state import State, STANDARD_SCRABBLE_DISTRIBUTION


def print_game_state(state: State) -> None:
    """Print a formatted representation of the current game state.
    
    Parameters
    ----------
    state : State
        The current game state to display
    """
    print("\n" + "="*60)
    print("CURRENT GAME STATE")
    print("="*60)
    
    # Print player scores and words
    for player in range(state.num_players):
        words_str = ", ".join([word.word for word in state.words_per_player[player]])
        if not words_str:
            words_str = "(no words)"
        print(f"Player {player + 1}: Score = {state.scores[player]}, Words = {words_str}")
    
    # Print pool letters
    pool_letters = []
    for letter_idx in range(26):
        letter = chr(ord('a') + letter_idx)
        count = int(state.pool[letter_idx])
        if count > 0:
            pool_letters.extend([letter] * count)
    
    if pool_letters:
        pool_str = ", ".join(sorted(pool_letters))
    else:
        pool_str = "(empty)"
    
    print(f"\nPool Letters: {pool_str}")
    
    # Print remaining letters in bag
    bag_total = int(sum(state.bag))
    print(f"Letters remaining in bag: {bag_total}")
    print("="*60)


def print_help() -> None:
    """Print help message with available commands."""
    print("\nAVAILABLE COMMANDS:")
    print("  PLAYER_NUM WORD  - Player attempts to make a word (e.g., '1 cat')")
    print("  draw             - Draw next letter from bag to pool")
    print("  end              - End the game and show final scores")
    print("  help             - Show this help message")
    print("  quit             - Exit without ending game")
    print()


def main():
    """Main driver function for the interactive Grab game."""
    parser = argparse.ArgumentParser(description='Interactive Grab word game')
    parser.add_argument('num_players', type=int, help='Number of players (1-4)')
    parser.add_argument('--word-list', default='twl06', choices=['twl06', 'sowpods'],
                       help='Word list to use (default: twl06)')
    
    args = parser.parse_args()
    
    if args.num_players < 1 or args.num_players > 4:
        print("Error: Number of players must be between 1 and 4")
        sys.exit(1)
    
    # Initialize the game
    try:
        game = Grab(word_list=args.word_list)
    except Exception as e:
        print(f"Error initializing game: {e}")
        sys.exit(1)
    
    # Create initial game state
    state = State(
        num_players=args.num_players,
        words_per_player=[[] for _ in range(args.num_players)],
        pool=np.zeros(26),
        bag=STANDARD_SCRABBLE_DISTRIBUTION.copy(),
        scores=np.zeros(args.num_players, dtype=int)
    )
    
    print(f"Welcome to Grab! Playing with {args.num_players} players using {args.word_list} word list.")
    print_help()
    print_game_state(state)
    
    # Main game loop
    while True:
        try:
            command = input("\nEnter command: ").strip().lower()
            
            if not command:
                continue
            
            if command == 'quit':
                print("Goodbye!")
                break
            
            elif command == 'help':
                print_help()
                continue
            
            elif command == 'draw':
                try:
                    move, new_state = game.construct_draw_letters(state)
                    drawn_letters = ", ".join(move.letters)
                    print(f"\nDrew letter(s): {drawn_letters}")
                    state = new_state
                    print_game_state(state)
                except ValueError as e:
                    print(f"\nError drawing letters: {e}")
            
            elif command == 'end':
                final_state = game.end_game(state)
                print("\nGAME ENDED!")
                print_game_state(final_state)
                
                # Find and announce winner(s)
                max_score = max(final_state.scores)
                winners = [i + 1 for i, score in enumerate(final_state.scores) if score == max_score]
                
                if len(winners) == 1:
                    print(f"\n🎉 Player {winners[0]} wins with {max_score} points! 🎉")
                else:
                    winners_str = ", ".join([f"Player {w}" for w in winners])
                    print(f"\n🎉 Tie game! Winners: {winners_str} with {max_score} points each! 🎉")
                break
            
            else:
                # Try to parse as "PLAYER_NUM WORD"
                parts = command.split()
                if len(parts) != 2:
                    print("Invalid command. Type 'help' for available commands.")
                    continue
                
                try:
                    player_num = int(parts[0])
                    word = parts[1]
                    
                    if player_num < 1 or player_num > args.num_players:
                        print(f"Invalid player number. Must be between 1 and {args.num_players}.")
                        continue
                    
                    player_idx = player_num - 1  # Convert to 0-based index
                    
                    # Attempt to make the word
                    move, new_state = game.construct_move(state, player_idx, word)
                    
                    print(f"\n✅ Player {player_num} successfully made '{word}'!")
                    
                    # Show what was used
                    if move.pool_letters:
                        pool_used = ", ".join(sorted(move.pool_letters))
                        print(f"   Used from pool: {pool_used}")
                    
                    if move.other_player_words:
                        other_words = []
                        for other_player, other_word in move.other_player_words:
                            other_words.append(f"Player {other_player + 1}'s '{other_word}'")
                        print(f"   Took words: {'; '.join(other_words)}")
                    
                    # Show score gained
                    score_gained = new_state.scores[player_idx] - state.scores[player_idx]
                    print(f"   Points gained: {score_gained}")
                    
                    state = new_state
                    print_game_state(state)
                    
                except ValueError:
                    print("Invalid player number. Must be a number.")
                except DisallowedWordException as e:
                    print(f"\n❌ '{word}' is not a valid word in the {args.word_list} word list.")
                except NoWordFoundException as e:
                    print(f"\n❌ Cannot make '{word}' with available letters and words.")
                except Exception as e:
                    print(f"\n❌ Error: {e}")
        
        except KeyboardInterrupt:
            print("\n\nGame interrupted. Goodbye!")
            break
        except EOFError:
            print("\n\nGoodbye!")
            break


if __name__ == '__main__':
    main()
