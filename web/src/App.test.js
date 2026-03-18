/**
 * Tests for the App root component.
 * Verifies authentication flow, socket lifecycle, screen routing, and event handling.
 */
import React from 'react';
import { render, screen, fireEvent, act, cleanup } from '@testing-library/react';

// Build the mock socket fresh for each test via a factory.
// We store the "current" mock socket in a module-level variable that gets
// reassigned in beforeEach, so the jest.mock factory always returns the latest one.
let mockCurrentSocket;
let mockCurrentHandlers;

function buildMockSocket() {
  const handlers = {};
  const socket = {
    on: jest.fn((event, handler) => {
      if (!handlers[event]) handlers[event] = [];
      handlers[event].push(handler);
    }),
    emit: jest.fn(),
    connect: jest.fn(),
    disconnect: jest.fn(),
    connected: true
  };
  return { socket, handlers };
}

function simulateSocketEvent(event, data) {
  if (mockCurrentHandlers[event]) {
    mockCurrentHandlers[event].forEach(h => h(data));
  }
}

// Mock socket.io-client to return whatever mockCurrentSocket is set to.
jest.mock('socket.io-client', () => {
  // This factory runs once, but the returned fn closes over the module-level variable
  // which gets reassigned each beforeEach.
  return function mockIo() {
    return mockCurrentSocket;
  };
});

import App from './App';

describe('App', () => {
  beforeEach(() => {
    const { socket, handlers } = buildMockSocket();
    mockCurrentSocket = socket;
    mockCurrentHandlers = handlers;

    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});

    global.fetch = jest.fn();
  });

  afterEach(() => {
    cleanup();
    console.log.mockRestore();
    console.error.mockRestore();
    global.fetch = undefined;
  });

  /**
   * Set up fetch to handle login (first call) and subsequent GameLobby fetches.
   */
  function setupFetchForLoginAndLobby() {
    let callCount = 0;
    global.fetch = jest.fn(() => {
      callCount++;
      if (callCount === 1) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: { player_id: 'uuid-1', username: 'testuser', session_token: 'token123' }
          }),
          text: () => Promise.resolve('{}')
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, data: { games: [], total_games: 0 } }),
        text: () => Promise.resolve('{}')
      });
    });
  }

  /**
   * Log in and connect socket, advancing to the lobby screen.
   */
  async function loginAndConnect() {
    setupFetchForLoginAndLobby();

    await act(async () => {
      render(<App />);
    });

    const loginBtn = screen.getByText(/Join Game Lobby/);
    await act(async () => {
      fireEvent.click(loginBtn);
    });

    await act(async () => {
      simulateSocketEvent('connect');
      simulateSocketEvent('connected', { message: 'Successfully connected' });
    });
  }

  /**
   * Enter a game from the lobby via game_state socket event.
   */
  async function enterGame() {
    const gameState = {
      game_id: 'TEST1',
      game_type: 'grab',
      status: 'active',
      current_turn: 1,
      turn_time_remaining: null,
      players: {
        testuser: { connected: true, score: 0, ready_for_next_turn: false }
      },
      state: JSON.stringify({
        num_players: 1,
        pool: new Array(26).fill(0),
        bag: new Array(26).fill(0),
        words_per_player: [[]],
        scores: [0],
        passed: [false]
      })
    };

    await act(async () => {
      simulateSocketEvent('game_state', { data: gameState });
    });

    return gameState;
  }

  test('shows login screen initially', () => {
    render(<App />);
    expect(screen.getByText(/Join Game Lobby/)).toBeInTheDocument();
  });

  test('login sends POST to auth endpoint', async () => {
    setupFetchForLoginAndLobby();

    await act(async () => {
      render(<App />);
    });

    await act(async () => {
      fireEvent.click(screen.getByText(/Join Game Lobby/));
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/auth/login'),
      expect.objectContaining({ method: 'POST' })
    );
  });

  test('login failure shows error status', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        status: 409,
        text: () => Promise.resolve('Username taken'),
        json: () => Promise.resolve({ success: false, error: 'Username taken' })
      })
    );

    await act(async () => {
      render(<App />);
    });

    await act(async () => {
      fireEvent.click(screen.getByText(/Join Game Lobby/));
    });

    expect(screen.getByText(/Login failed/)).toBeInTheDocument();
  });

  test('after connection, shows lobby with Disconnect button', async () => {
    await loginAndConnect();

    expect(screen.getByText('Disconnect')).toBeInTheDocument();
    expect(screen.getByText(/Game Lobby/)).toBeInTheDocument();
  });

  test('socket game_state event switches to GameInterface', async () => {
    await loginAndConnect();
    await enterGame();

    expect(screen.getByText(/Game TEST1/)).toBeInTheDocument();
  });

  test('socket move_result with error adds error event', async () => {
    await loginAndConnect();
    await enterGame();

    await act(async () => {
      simulateSocketEvent('move_result', {
        success: false,
        error: "Word 'xyz' is not in the allowed word list"
      });
    });

    expect(screen.getByText(/Word 'xyz' is not in the allowed word list/)).toBeInTheDocument();
  });

  test('socket player_disconnected adds connection event', async () => {
    await loginAndConnect();
    await enterGame();

    await act(async () => {
      simulateSocketEvent('player_disconnected', { player: 'otherPlayer' });
    });

    expect(screen.getByText(/otherPlayer disconnected/)).toBeInTheDocument();
  });

  test('socket player_reconnected adds connection event', async () => {
    await loginAndConnect();
    await enterGame();

    await act(async () => {
      simulateSocketEvent('player_reconnected', { player: 'otherPlayer' });
    });

    expect(screen.getByText(/otherPlayer reconnected/)).toBeInTheDocument();
  });

  test('socket game_ended returns to lobby', async () => {
    await loginAndConnect();
    await enterGame();

    await act(async () => {
      simulateSocketEvent('game_ended', { ended_by: 'host', reason: 'Game ended by creator' });
    });

    expect(screen.getByText(/Game Lobby/)).toBeInTheDocument();
  });

  test('turn_starting adds game event', async () => {
    await loginAndConnect();
    await enterGame();

    await act(async () => {
      simulateSocketEvent('turn_starting', {
        turn_number: 2,
        letters_drawn: ['e'],
        time_limit: 300,
        letters_remaining_in_bag: 85
      });
    });

    expect(screen.getByText(/Turn 2 starting/)).toBeInTheDocument();
  });

  test('turn_ending adds game event', async () => {
    await loginAndConnect();
    await enterGame();

    await act(async () => {
      simulateSocketEvent('turn_ending', {
        turn_number: 1,
        reason: 'all_players_passed',
        final_moves_count: 3
      });
    });

    expect(screen.getByText(/Turn 1 ended.*All players passed/)).toBeInTheDocument();
  });

  test('disconnect button returns to login screen', async () => {
    await loginAndConnect();

    await act(async () => {
      fireEvent.click(screen.getByText('Disconnect'));
    });

    expect(screen.getByText(/Join Game Lobby/)).toBeInTheDocument();
  });
});
