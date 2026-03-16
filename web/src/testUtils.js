/**
 * Shared test utilities and fixtures for frontend unit tests.
 * Provides mock factories for sockets, fetch, and game state objects.
 */

/**
 * Create a mock Socket.IO socket object with event simulation support.
 *
 * Returns
 * -------
 * object
 *     Mock socket with on, emit, connect, disconnect as jest.fn()s,
 *     plus simulateEvent(name, data) to invoke registered handlers.
 */
export function createMockSocket() {
  const handlers = {};

  const socket = {
    on: jest.fn((event, handler) => {
      if (!handlers[event]) {
        handlers[event] = [];
      }
      handlers[event].push(handler);
    }),
    emit: jest.fn(),
    connect: jest.fn(),
    disconnect: jest.fn(),
    connected: true,

    /**
     * Fire all handlers registered for a given event.
     *
     * Parameters
     * ----------
     * event : string
     *     The event name.
     * data : any
     *     The payload to pass to each handler.
     */
    simulateEvent: (event, data) => {
      if (handlers[event]) {
        handlers[event].forEach(handler => handler(data));
      }
    },

    /**
     * Clear all registered event handlers.
     */
    resetHandlers: () => {
      Object.keys(handlers).forEach(key => delete handlers[key]);
    }
  };

  return socket;
}

/**
 * Set up global.fetch to return a successful JSON response.
 *
 * Parameters
 * ----------
 * data : object
 *     The data field to include in the { success: true, data } response.
 *
 * Returns
 * -------
 * jest.Mock
 *     The mock fetch function for additional assertions.
 */
export function mockFetchSuccess(data) {
  const mockFetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ success: true, data }),
      text: () => Promise.resolve(JSON.stringify({ success: true, data }))
    })
  );
  global.fetch = mockFetch;
  return mockFetch;
}

/**
 * Set up global.fetch to return an error response.
 *
 * Parameters
 * ----------
 * status : number
 *     HTTP status code (e.g. 400, 500).
 * error : string
 *     Error message to include in the response body.
 *
 * Returns
 * -------
 * jest.Mock
 *     The mock fetch function for additional assertions.
 */
export function mockFetchError(status, error) {
  const mockFetch = jest.fn(() =>
    Promise.resolve({
      ok: false,
      status,
      json: () => Promise.resolve({ success: false, error }),
      text: () => Promise.resolve(JSON.stringify({ success: false, error }))
    })
  );
  global.fetch = mockFetch;
  return mockFetch;
}

/**
 * Create a realistic mock game state object with sensible defaults.
 * The state field is a JSON string matching the server's format.
 *
 * Parameters
 * ----------
 * overrides : object, optional
 *     Properties to override on the top-level game state object.
 * stateOverrides : object, optional
 *     Properties to override within the parsed state (pool, bag, words_per_player, etc.).
 *
 * Returns
 * -------
 * object
 *     A game state object matching the server's game_state event format.
 */
export function createMockGameState(overrides = {}, stateOverrides = {}) {
  const innerState = {
    num_players: 2,
    pool: [1, 0, 1, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    bag: [7, 2, 1, 3, 10, 2, 2, 2, 8, 1, 1, 3, 2, 5, 7, 2, 1, 5, 3, 5, 3, 2, 2, 1, 2, 1],
    words_per_player: [['hello'], ['world']],
    scores: [8, 9],
    passed: [false, false],
    ...stateOverrides
  };

  return {
    game_id: 'TEST1',
    game_type: 'grab',
    status: 'active',
    current_turn: 1,
    turn_time_remaining: null,
    players: {
      player1: { connected: true, score: 8, ready_for_next_turn: false },
      player2: { connected: true, score: 9, ready_for_next_turn: false }
    },
    state: JSON.stringify(innerState),
    ...overrides
  };
}

/**
 * Create a mock players map with defaults.
 *
 * Parameters
 * ----------
 * overrides : object, optional
 *     Properties to merge into the default players map.
 *
 * Returns
 * -------
 * object
 *     A players map keyed by username with connected, score, and ready_for_next_turn fields.
 */
export function createMockPlayers(overrides = {}) {
  return {
    player1: { connected: true, score: 8, ready_for_next_turn: false },
    player2: { connected: true, score: 9, ready_for_next_turn: false },
    ...overrides
  };
}
