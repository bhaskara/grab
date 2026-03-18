/**
 * Tests for the GameOverScreen component.
 * Verifies game over display, winner announcement, scores, and countdown behavior.
 */
import React from 'react';
import { render, screen, act } from '@testing-library/react';
import GameOverScreen from './GameOverScreen';

describe('GameOverScreen', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  const defaultGameOverData = {
    reason: 'All letters used',
    final_scores: { player1: 45, player2: 38 },
    winner: 'player1'
  };

  test('returns null when gameOverData is null', () => {
    const { container } = render(
      <GameOverScreen
        gameOverData={null}
        currentUsername="player1"
        onReturnToLobby={jest.fn()}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  test('shows "GAME OVER!" text', () => {
    render(
      <GameOverScreen
        gameOverData={defaultGameOverData}
        currentUsername="player1"
        onReturnToLobby={jest.fn()}
      />
    );
    expect(screen.getByText(/GAME OVER!/)).toBeInTheDocument();
  });

  test('shows "YOU WON!" when winner is current user', () => {
    render(
      <GameOverScreen
        gameOverData={defaultGameOverData}
        currentUsername="player1"
        onReturnToLobby={jest.fn()}
      />
    );
    expect(screen.getByText(/YOU WON!/)).toBeInTheDocument();
  });

  test('shows winner name when winner is a different player', () => {
    render(
      <GameOverScreen
        gameOverData={defaultGameOverData}
        currentUsername="player2"
        onReturnToLobby={jest.fn()}
      />
    );
    expect(screen.getByText(/player1 WINS!/)).toBeInTheDocument();
  });

  test('renders sorted final scores with ranks', () => {
    render(
      <GameOverScreen
        gameOverData={defaultGameOverData}
        currentUsername="spectator"
        onReturnToLobby={jest.fn()}
      />
    );
    // player1 has 45 (rank 1), player2 has 38 (rank 2)
    expect(screen.getByText('45 pts')).toBeInTheDocument();
    expect(screen.getByText('38 pts')).toBeInTheDocument();
    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('#2')).toBeInTheDocument();
  });

  test('shows "(You)" next to current player in scores', () => {
    render(
      <GameOverScreen
        gameOverData={defaultGameOverData}
        currentUsername="player2"
        onReturnToLobby={jest.fn()}
      />
    );
    expect(screen.getByText(/player2/)).toBeInTheDocument();
    expect(screen.getByText(/\(You\)/)).toBeInTheDocument();
  });

  test('countdown decrements each second', () => {
    render(
      <GameOverScreen
        gameOverData={defaultGameOverData}
        currentUsername="player1"
        onReturnToLobby={jest.fn()}
      />
    );

    expect(screen.getByText(/5 seconds/)).toBeInTheDocument();

    act(() => { jest.advanceTimersByTime(1000); });
    expect(screen.getByText(/4 seconds/)).toBeInTheDocument();

    act(() => { jest.advanceTimersByTime(1000); });
    expect(screen.getByText(/3 seconds/)).toBeInTheDocument();
  });

  test('"Return to Lobby Now" button calls onReturnToLobby', () => {
    const onReturn = jest.fn();
    render(
      <GameOverScreen
        gameOverData={defaultGameOverData}
        currentUsername="player1"
        onReturnToLobby={onReturn}
      />
    );

    const button = screen.getByText('Return to Lobby Now');
    button.click();
    expect(onReturn).toHaveBeenCalledTimes(1);
  });
});
