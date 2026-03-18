/**
 * Tests for the GameInterface component.
 * Verifies game layout rendering, state display, and user interactions.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import GameInterface from './GameInterface';
import { createMockGameState, createMockSocket, mockFetchSuccess } from './testUtils';

describe('GameInterface', () => {
  let mockSocket;

  const createDefaultProps = (overrides = {}) => ({
    gameState: createMockGameState(),
    socket: mockSocket,
    currentUsername: 'player1',
    authToken: 'test-token',
    serverUrl: 'http://localhost:5001',
    gameEvents: [],
    gameCreator: 'player1',
    onAddGameEvent: jest.fn(),
    onLeaveGame: jest.fn(),
    ...overrides
  });

  beforeEach(() => {
    mockSocket = createMockSocket();
    jest.clearAllMocks();
    // Suppress console.log/error from component
    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    console.log.mockRestore();
    console.error.mockRestore();
    if (global.fetch) {
      global.fetch = undefined;
    }
  });

  test('shows loading when gameState is null', () => {
    render(<GameInterface {...createDefaultProps({ gameState: null })} />);
    expect(screen.getByText(/Loading game/)).toBeInTheDocument();
  });

  test('renders game ID in header', () => {
    render(<GameInterface {...createDefaultProps()} />);
    expect(screen.getByText(/Game TEST1/)).toBeInTheDocument();
  });

  test('renders game status in header', () => {
    render(<GameInterface {...createDefaultProps()} />);
    expect(screen.getByText(/ACTIVE/)).toBeInTheDocument();
  });

  test('renders turn info in header', () => {
    render(<GameInterface {...createDefaultProps()} />);
    expect(screen.getByText(/Turn: 1/)).toBeInTheDocument();
  });

  test('shows remaining letters count', () => {
    render(<GameInterface {...createDefaultProps()} />);
    // The bag has letters, so "Remaining letters" should appear with a count
    expect(screen.getByText(/Remaining letters/)).toBeInTheDocument();
  });

  test('shows "Start Game" button for creator in waiting state', () => {
    const gameState = createMockGameState({ status: 'waiting' });
    render(<GameInterface {...createDefaultProps({ gameState, gameCreator: 'player1' })} />);
    expect(screen.getByText(/START GAME/)).toBeInTheDocument();
  });

  test('shows "Waiting for" message for non-creator in waiting state', () => {
    const gameState = createMockGameState({ status: 'waiting' });
    render(<GameInterface {...createDefaultProps({ gameState, gameCreator: 'otherPlayer' })} />);
    expect(screen.getByText(/Waiting for the game creator/)).toBeInTheDocument();
  });

  test('start game sends POST request', async () => {
    const mockFetch = mockFetchSuccess({ game_id: 'TEST1', status: 'active' });
    const gameState = createMockGameState({ status: 'waiting' });
    const onAddGameEvent = jest.fn();

    render(
      <GameInterface
        {...createDefaultProps({ gameState, gameCreator: 'player1', onAddGameEvent })}
      />
    );

    await act(async () => {
      fireEvent.click(screen.getByText(/START GAME/));
    });

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:5001/api/games/TEST1/start',
      expect.objectContaining({ method: 'POST' })
    );
  });

  test('child components are rendered', () => {
    render(<GameInterface {...createDefaultProps()} />);
    // LetterPool
    expect(screen.getByText(/Available Letters/)).toBeInTheDocument();
    // PlayerWords
    expect(screen.getByText(/Players/)).toBeInTheDocument();
    // WordInput
    expect(screen.getByText(/Command Input/)).toBeInTheDocument();
    // GameLog
    expect(screen.getByText(/Game Log/)).toBeInTheDocument();
  });

  test('handleSubmitWord emits socket move event', () => {
    render(<GameInterface {...createDefaultProps()} />);

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'hello' } });
    fireEvent.submit(input.closest('form'));

    expect(mockSocket.emit).toHaveBeenCalledWith('move', { data: 'hello' });
  });
});
