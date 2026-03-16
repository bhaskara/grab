/**
 * Tests for the PlayerWords component.
 * Verifies player display, word rendering, scores, and edge cases.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import PlayerWords from './PlayerWords';
import { createMockGameState, createMockPlayers } from './testUtils';

describe('PlayerWords', () => {
  test('renders player usernames', () => {
    const gameState = createMockGameState();
    render(
      <PlayerWords
        players={gameState.players}
        gameState={gameState}
        currentUsername="player1"
      />
    );
    expect(screen.getByText(/player1/)).toBeInTheDocument();
    expect(screen.getByText(/player2/)).toBeInTheDocument();
  });

  test('highlights current player with "(You)"', () => {
    const gameState = createMockGameState();
    render(
      <PlayerWords
        players={gameState.players}
        gameState={gameState}
        currentUsername="player1"
      />
    );
    expect(screen.getByText(/\(You\)/)).toBeInTheDocument();
  });

  test('shows Online/Offline status', () => {
    const players = {
      player1: { connected: true, score: 0, ready_for_next_turn: false },
      player2: { connected: false, score: 0, ready_for_next_turn: false }
    };
    const gameState = createMockGameState({ players });
    render(
      <PlayerWords
        players={players}
        gameState={gameState}
        currentUsername="player1"
      />
    );
    expect(screen.getByText(/Online/)).toBeInTheDocument();
    expect(screen.getByText(/Offline/)).toBeInTheDocument();
  });

  test('shows "No words yet" for empty word list', () => {
    const gameState = createMockGameState({}, { words_per_player: [[], []] });
    render(
      <PlayerWords
        players={gameState.players}
        gameState={gameState}
        currentUsername="player1"
      />
    );
    const noWordsEls = screen.getAllByText(/No words yet/);
    expect(noWordsEls).toHaveLength(2);
  });

  test('renders word tiles with uppercase text', () => {
    const gameState = createMockGameState({}, { words_per_player: [['hello'], ['world']] });
    render(
      <PlayerWords
        players={gameState.players}
        gameState={gameState}
        currentUsername="player1"
      />
    );
    expect(screen.getByText('HELLO')).toBeInTheDocument();
    expect(screen.getByText('WORLD')).toBeInTheDocument();
  });

  test('renders calculated word scores next to words', () => {
    // hello = h(4)+e(1)+l(1)+l(1)+o(1) = 8
    const gameState = createMockGameState({}, { words_per_player: [['hello'], []] });
    render(
      <PlayerWords
        players={gameState.players}
        gameState={gameState}
        currentUsername="player1"
      />
    );
    expect(screen.getByText('HELLO')).toBeInTheDocument();
    // Word score chip should show "8"
    expect(screen.getByText('8')).toBeInTheDocument();
  });

  test('shows player total scores', () => {
    const gameState = createMockGameState({}, { scores: [15, 23] });
    render(
      <PlayerWords
        players={gameState.players}
        gameState={gameState}
        currentUsername="player1"
      />
    );
    expect(screen.getByText('15 pts')).toBeInTheDocument();
    expect(screen.getByText('23 pts')).toBeInTheDocument();
  });

  test('handles null/missing game state gracefully', () => {
    render(
      <PlayerWords
        players={null}
        gameState={null}
        currentUsername="player1"
      />
    );
    expect(screen.getByText(/No game data available/)).toBeInTheDocument();
  });

  test('handles state as JSON string', () => {
    const gameState = createMockGameState();
    // state is already a JSON string from createMockGameState
    expect(typeof gameState.state).toBe('string');
    render(
      <PlayerWords
        players={gameState.players}
        gameState={gameState}
        currentUsername="player1"
      />
    );
    // Should parse and render without errors
    expect(screen.getByText('HELLO')).toBeInTheDocument();
  });
});
