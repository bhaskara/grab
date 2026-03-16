/**
 * Tests for the GameLog component.
 * Verifies message rendering, formatting, prefixes, and limiting behavior.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import GameLog from './GameLog';

/**
 * Helper to create a message object matching the format used by the app.
 *
 * Parameters
 * ----------
 * type : string
 *     Message type (system, error, success, move, connection, game_event).
 * text : string
 *     Message text content.
 * timestamp : number, optional
 *     Unix timestamp in ms. Defaults to Date.now().
 *
 * Returns
 * -------
 * object
 *     A message object with timestamp, type, and text fields.
 */
function makeMessage(type, text, timestamp = Date.now()) {
  return { timestamp, type, text };
}

describe('GameLog', () => {
  test('renders "Game Log" heading', () => {
    render(<GameLog messages={[]} />);
    expect(screen.getByText(/Game Log/)).toBeInTheDocument();
  });

  test('shows empty state when messages array is empty', () => {
    render(<GameLog messages={[]} />);
    expect(screen.getByText(/Game log is empty/)).toBeInTheDocument();
  });

  test('renders messages with [SYS] prefix for system type', () => {
    const messages = [makeMessage('system', 'Welcome to the game')];
    render(<GameLog messages={messages} />);
    expect(screen.getByText(/\[SYS\].*Welcome to the game/)).toBeInTheDocument();
  });

  test('renders messages with correct prefixes per type', () => {
    const messages = [
      makeMessage('error', 'Something broke'),
      makeMessage('success', 'Move worked'),
      makeMessage('move', 'Playing HELLO'),
      makeMessage('connection', 'player1 connected'),
      makeMessage('game_event', 'Turn starting'),
    ];
    render(<GameLog messages={messages} />);

    expect(screen.getByText(/\[ERR\].*Something broke/)).toBeInTheDocument();
    expect(screen.getByText(/\[OK\].*Move worked/)).toBeInTheDocument();
    expect(screen.getByText(/\[MOVE\].*Playing HELLO/)).toBeInTheDocument();
    expect(screen.getByText(/\[CONN\].*player1 connected/)).toBeInTheDocument();
    expect(screen.getByText(/\[GAME\].*Turn starting/)).toBeInTheDocument();
  });

  test('respects maxMessages prop', () => {
    const messages = Array.from({ length: 10 }, (_, i) =>
      makeMessage('system', `Message ${i}`)
    );
    render(<GameLog messages={messages} maxMessages={3} />);
    // Should only show last 3 messages
    expect(screen.queryByText(/Message 6/)).not.toBeInTheDocument();
    expect(screen.getByText(/Message 7/)).toBeInTheDocument();
    expect(screen.getByText(/Message 8/)).toBeInTheDocument();
    expect(screen.getByText(/Message 9/)).toBeInTheDocument();
  });

  test('shows timestamps on messages', () => {
    // Use a fixed timestamp: 2025-01-15 at 14:30:45 UTC
    const ts = new Date('2025-01-15T14:30:45Z').getTime();
    const messages = [makeMessage('system', 'Test message', ts)];
    render(<GameLog messages={messages} />);
    // The formatted time should appear somewhere (locale-dependent, so use regex)
    const messageEl = screen.getByText(/\[SYS\].*Test message/);
    // Should contain a time pattern like HH:MM:SS
    expect(messageEl.textContent).toMatch(/\d{2}:\d{2}:\d{2}/);
  });
});
