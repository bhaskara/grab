/**
 * Tests for the GameLobby component.
 * Verifies game list fetching, game creation, joining, and auto-refresh behavior.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import GameLobby from './GameLobby';
import { mockFetchSuccess, mockFetchError } from './testUtils';

describe('GameLobby', () => {
  const defaultProps = {
    serverUrl: 'http://localhost:5001',
    authToken: 'test-token',
    onGameJoined: jest.fn(),
    onGameCreated: jest.fn()
  };

  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.useRealTimers();
    if (global.fetch) {
      global.fetch = undefined;
    }
  });

  const sampleGames = [
    {
      game_id: 'ABC123',
      status: 'waiting',
      max_players: 4,
      current_players: [{ username: 'host', joined_at: '2025-01-15T10:00:00Z' }],
      creator_id: 'uuid-1',
      created_at: '2025-01-15T10:00:00Z',
      started_at: null,
      finished_at: null,
      tileset: 'standard'
    },
    {
      game_id: 'DEF456',
      status: 'active',
      max_players: 4,
      current_players: [
        { username: 'host2', joined_at: '2025-01-15T10:00:00Z' },
        { username: 'guest', joined_at: '2025-01-15T10:01:00Z' }
      ],
      creator_id: 'uuid-2',
      created_at: '2025-01-15T10:00:00Z',
      started_at: '2025-01-15T10:02:00Z',
      finished_at: null,
      tileset: 'standard'
    }
  ];

  test('fetches game list on mount', async () => {
    const mockFetch = mockFetchSuccess({ games: sampleGames, total_games: 2 });

    await act(async () => {
      render(<GameLobby {...defaultProps} />);
    });

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:5001/api/games',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token'
        })
      })
    );
  });

  test('renders game list with status and players', async () => {
    mockFetchSuccess({ games: sampleGames, total_games: 2 });

    await act(async () => {
      render(<GameLobby {...defaultProps} />);
    });

    expect(screen.getByText(/ABC123/)).toBeInTheDocument();
    expect(screen.getByText(/DEF456/)).toBeInTheDocument();
    expect(screen.getByText(/WAITING/)).toBeInTheDocument();
    expect(screen.getByText(/ACTIVE/)).toBeInTheDocument();
  });

  test('shows "No games available" for empty list', async () => {
    mockFetchSuccess({ games: [], total_games: 0 });

    await act(async () => {
      render(<GameLobby {...defaultProps} />);
    });

    expect(screen.getByText(/No games available/)).toBeInTheDocument();
  });

  test('shows error on fetch failure', async () => {
    mockFetchError(500, 'Server error');

    await act(async () => {
      render(<GameLobby {...defaultProps} />);
    });

    expect(screen.getByText(/Error/i)).toBeInTheDocument();
  });

  test('"Create New Game" toggles create panel', async () => {
    mockFetchSuccess({ games: [], total_games: 0 });

    await act(async () => {
      render(<GameLobby {...defaultProps} />);
    });

    // Click to open create panel
    const createBtn = screen.getByText(/Create New Game/);
    fireEvent.click(createBtn);

    // Tileset selector should appear
    expect(screen.getByLabelText(/Tileset/)).toBeInTheDocument();

    // Click again to close (button text changes to "Cancel")
    const cancelBtn = screen.getByText('Cancel');
    fireEvent.click(cancelBtn);

    // Tileset selector should be gone
    expect(screen.queryByLabelText(/Tileset/)).not.toBeInTheDocument();
  });

  test('creating a game sends POST with tileset', async () => {
    // First call returns empty list, second call (after create) returns new game
    let callCount = 0;
    global.fetch = jest.fn(() => {
      callCount++;
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: callCount <= 1
            ? { games: [], total_games: 0 }
            : { game_id: 'NEW1', status: 'waiting' }
        }),
        text: () => Promise.resolve('{}')
      });
    });

    await act(async () => {
      render(<GameLobby {...defaultProps} />);
    });

    // Open create panel
    fireEvent.click(screen.getByText(/Create New Game/));

    // Click "Create Game" button
    await act(async () => {
      fireEvent.click(screen.getByText('Create Game'));
    });

    // Should have made a POST call
    const postCall = global.fetch.mock.calls.find(
      call => call[1] && call[1].method === 'POST'
    );
    expect(postCall).toBeDefined();
    expect(JSON.parse(postCall[1].body)).toHaveProperty('tileset', 'standard');
  });

  test('joining a game sends POST and calls onGameJoined', async () => {
    // Setup: first fetch returns game list, then join succeeds
    let callCount = 0;
    global.fetch = jest.fn(() => {
      callCount++;
      if (callCount === 1) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: { games: sampleGames, total_games: 2 } }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, data: { game_id: 'ABC123', player_id: 'uuid', joined_at: '2025-01-15T10:05:00Z' } }),
      });
    });

    await act(async () => {
      render(<GameLobby {...defaultProps} />);
    });

    // Click "Join Game" on the waiting game
    await act(async () => {
      fireEvent.click(screen.getByText(/Join Game/));
    });

    expect(defaultProps.onGameJoined).toHaveBeenCalledWith(
      'ABC123',
      expect.objectContaining({ game_id: 'ABC123' })
    );
  });

  test('auto-refreshes every 5 seconds', async () => {
    const mockFetch = mockFetchSuccess({ games: [], total_games: 0 });

    await act(async () => {
      render(<GameLobby {...defaultProps} />);
    });

    const initialCallCount = mockFetch.mock.calls.length;

    // Advance 5 seconds
    await act(async () => {
      jest.advanceTimersByTime(5000);
    });

    expect(mockFetch.mock.calls.length).toBeGreaterThan(initialCallCount);
  });

  test('clears interval on unmount', async () => {
    mockFetchSuccess({ games: [], total_games: 0 });

    let unmount;
    await act(async () => {
      const result = render(<GameLobby {...defaultProps} />);
      unmount = result.unmount;
    });

    const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
    unmount();
    expect(clearIntervalSpy).toHaveBeenCalled();
    clearIntervalSpy.mockRestore();
  });
});
