/**
 * Tests for the WordInput component.
 * Verifies word submission, command handling, input validation, and keyboard navigation.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import WordInput from './WordInput';
import { mockFetchSuccess, mockFetchError } from './testUtils';

describe('WordInput', () => {
  const defaultProps = {
    onSubmitWord: jest.fn(),
    onPass: jest.fn(),
    disabled: false,
    gameId: 'TEST1',
    currentUsername: 'player1',
    authToken: 'test-token',
    serverUrl: 'http://localhost:5001',
    gameCreator: 'player1',
    onAddGameEvent: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});
    if (global.fetch) {
      global.fetch = undefined;
    }
  });

  afterEach(() => {
    console.log.mockRestore();
    console.error.mockRestore();
  });

  test('renders prompt with game ID and username', () => {
    render(<WordInput {...defaultProps} />);
    expect(screen.getByText(/TEST1/)).toBeInTheDocument();
    expect(screen.getByText(/@player1/)).toBeInTheDocument();
  });

  test('submitting a word calls onSubmitWord with lowercase word', () => {
    render(<WordInput {...defaultProps} />);
    const input = screen.getByRole('textbox');

    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.submit(input.closest('form'));

    expect(defaultProps.onSubmitWord).toHaveBeenCalledWith('hello');
  });

  test('submitting empty input calls onPass', () => {
    render(<WordInput {...defaultProps} />);
    const input = screen.getByRole('textbox');

    fireEvent.submit(input.closest('form'));

    expect(defaultProps.onPass).toHaveBeenCalledTimes(1);
    expect(defaultProps.onSubmitWord).not.toHaveBeenCalled();
  });

  test('!ready calls onPass', () => {
    render(<WordInput {...defaultProps} />);
    const input = screen.getByRole('textbox');

    fireEvent.change(input, { target: { value: '!ready' } });
    fireEvent.submit(input.closest('form'));

    expect(defaultProps.onPass).toHaveBeenCalledTimes(1);
  });

  test('!help calls onAddGameEvent with system type', () => {
    render(<WordInput {...defaultProps} />);
    const input = screen.getByRole('textbox');

    fireEvent.change(input, { target: { value: '!help' } });
    fireEvent.submit(input.closest('form'));

    expect(defaultProps.onAddGameEvent).toHaveBeenCalledWith(
      'system',
      expect.stringContaining('Commands:')
    );
  });

  test('invalid input calls onAddGameEvent with error type', () => {
    render(<WordInput {...defaultProps} />);
    const input = screen.getByRole('textbox');

    fireEvent.change(input, { target: { value: 'abc123' } });
    fireEvent.submit(input.closest('form'));

    expect(defaultProps.onAddGameEvent).toHaveBeenCalledWith(
      'error',
      expect.stringContaining('Invalid command')
    );
  });

  test('input is cleared after submission', () => {
    render(<WordInput {...defaultProps} />);
    const input = screen.getByRole('textbox');

    fireEvent.change(input, { target: { value: 'hello' } });
    fireEvent.submit(input.closest('form'));

    expect(input.value).toBe('');
  });

  test('disabled state prevents submission', () => {
    render(<WordInput {...defaultProps} disabled={true} />);
    const input = screen.getByRole('textbox');

    fireEvent.change(input, { target: { value: 'hello' } });
    fireEvent.submit(input.closest('form'));

    expect(defaultProps.onSubmitWord).not.toHaveBeenCalled();
  });

  test('ArrowUp/ArrowDown navigate command history', () => {
    render(<WordInput {...defaultProps} />);
    const input = screen.getByRole('textbox');

    // Submit two commands to build history
    fireEvent.change(input, { target: { value: 'first' } });
    fireEvent.submit(input.closest('form'));

    fireEvent.change(input, { target: { value: 'second' } });
    fireEvent.submit(input.closest('form'));

    // ArrowUp should show most recent command
    fireEvent.keyDown(input, { key: 'ArrowUp' });
    expect(input.value).toBe('second');

    // ArrowUp again should show older command
    fireEvent.keyDown(input, { key: 'ArrowUp' });
    expect(input.value).toBe('first');

    // ArrowDown should go back to more recent
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    expect(input.value).toBe('second');

    // ArrowDown again should clear input
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    expect(input.value).toBe('');
  });

  test('!end sends DELETE fetch when user is creator', async () => {
    const mockFetch = mockFetchSuccess({ game_id: 'TEST1', status: 'finished' });

    render(<WordInput {...defaultProps} />);
    const input = screen.getByRole('textbox');

    fireEvent.change(input, { target: { value: '!end' } });
    fireEvent.submit(input.closest('form'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:5001/api/games/TEST1',
        expect.objectContaining({ method: 'DELETE' })
      );
    });
  });

  test('!end by non-creator shows error', () => {
    render(<WordInput {...defaultProps} gameCreator="otherPlayer" />);
    const input = screen.getByRole('textbox');

    fireEvent.change(input, { target: { value: '!end' } });
    fireEvent.submit(input.closest('form'));

    expect(defaultProps.onAddGameEvent).toHaveBeenCalledWith(
      'error',
      expect.stringContaining('Only the game creator')
    );
  });

  test('recent commands are displayed', () => {
    render(<WordInput {...defaultProps} />);
    const input = screen.getByRole('textbox');

    fireEvent.change(input, { target: { value: 'hello' } });
    fireEvent.submit(input.closest('form'));

    expect(screen.getByText(/Recent:/)).toBeInTheDocument();
    expect(screen.getByText(/hello/)).toBeInTheDocument();
  });
});
