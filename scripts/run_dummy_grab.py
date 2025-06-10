"""Runnable driver script to test the dummy grab implementation.

First, it prompts you for the player names.  Then, it prompts for
moves, where each move is of the form PLAYER_NAME: MOVE.  As
mentioned in the DummyGrab rules, MOVE may be empty.  After each
round, it prints the current history.  When the game is done,
this script terminates.

"""

import sys
import os

# Add the src directory to the path so we can import grab modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from grab.dummy_grab import DummyGrab


def get_player_names():
    """Get player names from user input."""
    print("Enter player names (one per line, empty line to finish):")
    players = []
    while True:
        name = input().strip()
        if not name:
            break
        players.append(name)
    return players


def display_game_state(game):
    """Display the current game state."""
    is_running, current_round, history = game.get_state()
    
    print(f"\n--- Game State ---")
    print(f"Round: {current_round}")
    print(f"Running: {is_running}")
    
    if history:
        print("History:")
        for summary in history:
            print(f"  {summary}")
    else:
        print("No round history yet.")
    print("------------------\n")


def main():
    """Main driver function."""
    print("=== Dummy Grab Game ===")
    
    # Get player names
    players = get_player_names()
    
    if len(players) < 1:
        print("Need at least one player to start the game.")
        return
    
    print(f"Starting game with players: {', '.join(players)}")
    
    # Initialize game
    game = DummyGrab(players)
    
    # Track previous round to detect round changes
    previous_round = 1
    
    # Main game loop
    while True:
        is_running, current_round, _ = game.get_state()
        
        if not is_running:
            print("Game finished!")
            display_game_state(game)
            break
        
        # Display state when round changes
        if current_round != previous_round:
            display_game_state(game)
            previous_round = current_round
        
        # Get player move
        print(f"Round {current_round} - Enter move (format: PLAYER_NAME: MOVE, or 'quit' to exit):")
        user_input = input().strip()
        
        if user_input.lower() == 'quit':
            break
        
        # Parse input
        if ':' not in user_input:
            print("Invalid format. Use: PLAYER_NAME: MOVE")
            continue
        
        player_name, move = user_input.split(':', 1)
        player_name = player_name.strip()
        move = move.strip()
        
        # Send move to game
        try:
            game.send_move(player_name, move)
        except ValueError as e:
            print(f"Error: {e}")
            continue


if __name__ == "__main__":
    main()
