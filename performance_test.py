#!/usr/bin/env python3
"""Performance test for construct_move optimizations.

This script benchmarks the construct_move method under various conditions
to ensure it remains fast enough for real-time gameplay.
"""

import time
import numpy as np
from src.grab.grab_game import Grab
from src.grab.grab_state import State, Word

def create_small_game_state():
    """Create a small game state for baseline testing."""
    game = Grab()
    state = State(num_players=2)
    
    # Add a few words
    state.words_per_player[0].append(Word("cat"))
    state.words_per_player[1].append(Word("dog"))
    
    # Add letters to pool
    state.pool[0] = 1  # 'a'
    state.pool[2] = 1  # 'c'  
    state.pool[18] = 1  # 's'
    state.pool[19] = 1  # 't'
    
    return game, state

def create_large_game_state():
    """Create a game state with many words to stress-test performance."""
    game = Grab()
    state = State(num_players=4)
    
    # Add many words to each player to stress-test the algorithm
    words_list = ["cat", "dog", "bird", "fish", "tree", "book", "word", "game", 
                  "test", "play", "work", "time", "hand", "life", "home"]
    for p in range(4):
        for word_str in words_list:
            state.words_per_player[p].append(Word(word_str))
    
    # Add letters to pool for various moves
    state.pool[0] = 3  # 'a'
    state.pool[2] = 3  # 'c'  
    state.pool[18] = 3  # 's'
    state.pool[19] = 3  # 't'
    state.pool[4] = 2  # 'e'
    state.pool[17] = 2  # 'r'
    
    return game, state

def benchmark_scenario(name, game, state, word, iterations=1000):
    """Benchmark a specific scenario."""
    print(f"\n{name}:")
    print(f"  Players: {state.num_players}")
    print(f"  Total words: {sum(len(words) for words in state.words_per_player)}")
    
    # Warm up
    for _ in range(10):
        try:
            game.construct_move(state, 0, word)
        except:
            pass
    
    # Benchmark
    start_time = time.perf_counter()
    successful_moves = 0
    
    for _ in range(iterations):
        try:
            move, new_state = game.construct_move(state, 0, word)
            successful_moves += 1
        except:
            pass
    
    end_time = time.perf_counter()
    avg_time = (end_time - start_time) / iterations
    
    print(f"  Average time: {avg_time*1000000:.1f}μs")
    print(f"  Success rate: {successful_moves}/{iterations}")
    
    # Check if it meets performance requirements (< 1000μs = 1ms)
    if avg_time < 0.001:
        print(f"  ✅ FAST (< 1ms)")
    elif avg_time < 0.01:
        print(f"  ⚠️  ACCEPTABLE (< 10ms)")
    else:
        print(f"  ❌ SLOW (> 10ms)")
    
    return avg_time

def main():
    """Run comprehensive performance benchmarks."""
    print("=== Grab Game construct_move Performance Benchmark ===")
    print("Target: Much faster than network latency (10-100ms)")
    
    # Test 1: Small game state - baseline
    game_small, state_small = create_small_game_state()
    benchmark_scenario("Small Game - Simple Move", game_small, state_small, "cats")
    
    # Test 2: Large game state - stress test
    game_large, state_large = create_large_game_state()
    benchmark_scenario("Large Game - Simple Move", game_large, state_large, "cats")
    
    # Test 3: Large game state - word reuse
    benchmark_scenario("Large Game - Word Reuse", game_large, state_large, "cater")
    
    # Test 4: Impossible word (early rejection)
    benchmark_scenario("Large Game - Impossible Word", game_large, state_large, "zzzzz")
    
    # Test 5: Long word
    benchmark_scenario("Large Game - Long Word", game_large, state_large, "concatenation")
    
    print("\n=== Summary ===")
    print("All scenarios should be < 1ms for excellent responsiveness")
    print("Network latency is typically 10-100ms, so we have plenty of headroom")

if __name__ == "__main__":
    main()