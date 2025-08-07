# Grab Game Web Frontend - Developer Brief

This is a development plan for a web frontend for the grab game.  It covers the high level architecture and an implementation plan in six steps.  There is also a "Testing plan" section at the end that describes how to test functionality after each step.

## Project Overview
Build a React web frontend for the existing Grab word game server. The game is similar to Scrabble where players form words using available letters and can "steal" other players' words to form new ones.

**Existing working components:**
- Flask-SocketIO server with HTTP + WebSocket APIs (see `doc/server-api.md`, `doc/websocket-api.md`)
- Terminal client (`scripts/socketio_client.py`) - use this for cross-testing

## Technical Requirements
- **Framework:** React (required)
- **Styling:** Terminal-like theme (dark background, monospace font)
- **Real-time:** Socket.IO client integration
- **Compatibility:** Must work alongside existing terminal client

## Development Steps

### Step 1: React Setup + Socket.IO
- Create React app with Socket.IO client
- Test basic connection to server

### Step 2: Authentication + Socket Connection
- Login form (username only, no password)
- JWT token storage in localStorage
- Authenticated Socket.IO connection

### Step 3: Lobby Interface
- List games, create games, join games
- HTTP API integration for game management

### Step 4: Terminal-like Game Interface
- Command-line style word input (`Game> `)
- Game state display (pool letters, player words, scores)
- Game log for move results and events

### Step 5: Real-time Features
- Handle all Socket.IO events (game_state, move_result, letters_drawn, etc.)
- Cross-client compatibility with terminal client

### Step 6: Polish & Error Handling
- Error messages, loading states, responsive design

## Key Code Patterns

### Socket.IO Connection
```javascript
import io from 'socket.io-client';

const socket = io('http://localhost:5000', {
  auth: { token: sessionToken }
});

// Required event handlers
socket.on('connected', (data) => { /* auth success */ });
socket.on('game_state', (data) => { /* update UI */ });
socket.on('move_result', (data) => { /* show success/error */ });
socket.on('letters_drawn', (data) => { /* show new letters */ });
```

### Making Moves
```javascript
// Word move
socket.emit('move', { data: 'hello' });

// Pass/ready for next turn  
socket.emit('player_action', { data: 'ready_for_next_turn' });

// Get current state
socket.emit('get_status');
```

## File Structure Suggestion
```
src/
├── components/
│   ├── Login.jsx
│   ├── Lobby.jsx  
│   ├── Game.jsx
│   ├── WordInput.jsx
│   └── GameState.jsx
├── hooks/
│   ├── useAuth.js
│   └── useSocket.js
├── services/
│   └── socketService.js
└── App.jsx
```

## Success Criteria
- Web and terminal clients can play in the same game simultaneously
- All moves/events synchronized in real-time across clients
- Terminal-like styling matches the aesthetic of command-line client
- Handles disconnections/errors gracefully

# Testing plan

## Step 1: React App Setup + Socket.IO Client

### What to test:
```bash
# 1. Basic React app runs
npm start
# Should see React default page at http://localhost:3000

# 2. Socket.IO client library installed
npm list socket.io-client
# Should show socket.io-client version

# 3. Can connect to your server
# In browser console:
import io from 'socket.io-client';
const socket = io('http://localhost:5000');
console.log(socket.connected); // Should eventually be true
```

### Success criteria:
- React dev server starts without errors
- Browser console shows no import errors
- Can establish basic Socket.IO connection to your server

---

## Step 2: Authentication Flow + Socket.IO Connection

### Manual test script:
```javascript
// Test in browser console after this step
const testAuth = async () => {
  // Test login
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'testuser' })
  });
  const result = await response.json();
  console.log('Login result:', result);
  
  // Should see: { success: true, data: { session_token: "...", ... } }
  
  // Test Socket.IO with token
  const socket = io('http://localhost:5000', {
    auth: { token: result.data.session_token }
  });
  
  socket.on('connected', (data) => {
    console.log('Socket.IO connected:', data);
  });
  
  socket.on('error', (error) => {
    console.error('Socket.IO error:', error);
  });
};

testAuth();
```

### Component test:
```javascript
// You should be able to:
// 1. Enter username in login form
// 2. Click login button
// 3. See successful login (user data displayed)
// 4. Browser localStorage should contain 'session_token'
// 5. Network tab should show successful Socket.IO connection
```

### Success criteria:
- Login form accepts username and makes API call
- JWT token stored in localStorage
- Socket.IO connection established with auth token
- Login state persists on page refresh

---

## Step 3: Lobby Components

### Test using your existing server:
```bash
# Start your server first
python run.py

# Then test these API endpoints manually:
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser"}'

# Use the token from above response:
curl -X POST http://localhost:5000/api/games \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{}'

curl -X GET http://localhost:5000/api/games \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Component tests:
```javascript
// Test checklist in the browser:
// 1. After login, should see lobby with "Create Game" button
// 2. Click "Create Game" - should see new game appear in list
// 3. Game list should show: Game ID, status "waiting", 0/4 players
// 4. Should be able to click "Join" on the created game
// 5. After joining, player count should show 1/4 players
// 6. Game list should auto-refresh (test by creating game in terminal client)
```

### Integration test script:
```javascript
// Run this in browser console to verify API integration:
const testLobby = async () => {
  const token = localStorage.getItem('session_token');
  
  // Create game
  const createResp = await fetch('/api/games', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({})
  });
  const game = await createResp.json();
  console.log('Created game:', game);
  
  // List games
  const listResp = await fetch('/api/games', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const games = await listResp.json();
  console.log('Games list:', games);
  
  // Join game (this requires Socket.IO connection first!)
  const joinResp = await fetch(`/api/games/${game.data.game_id}/join`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const joinResult = await joinResp.json();
  console.log('Join result:', joinResult);
};
```

### Success criteria:
- Can create games and see them in the list
- Game list updates in real-time
- Can join games (requires active Socket.IO connection)
- Error handling for full games, invalid games, etc.

---

## Step 4: Terminal-like Game Interface

### Test with your socketio_client.py:
```bash
# Terminal 1: Start your server
python run.py

# Terminal 2: Start terminal client
python scripts/socketio_client.py http://localhost:5000
# Enter username: terminaluser
# Create a game and join it

# Terminal 3: Test web client
# Open browser, login as different user, join same game
# Both clients should see the same game state
```

### Component functionality tests:
```javascript
// In browser console, after joining a game:
// 1. Test word input
document.querySelector('.word-input-field').value = 'test';
document.querySelector('.word-input form').dispatchEvent(new Event('submit'));

// 2. Test pass action
document.querySelector('.word-input-field').value = '!ready';
document.querySelector('.word-input form').dispatchEvent(new Event('submit'));

// 3. Verify game state display
console.log(document.querySelector('.game-state').textContent);
// Should show current game state
```

### Cross-client test:
1. **Terminal client**: Create game, join it
2. **Web client**: Join same game
3. **Terminal client**: Make a word (e.g., type "hello")
4. **Web client**: Should see the move in game log and updated state
5. **Web client**: Make a word
6. **Terminal client**: Should see the update

### Success criteria:
- Word input form works and sends moves via Socket.IO
- Game state displays current pool letters, player words, scores
- Game log shows move attempts and results
- Real-time updates work between web and terminal clients
- Pass/ready functionality works

---

## Step 5: Real-time Features

### Multi-client stress test:
```bash
# Start 3 terminal clients and 2 web clients all in same game
# Test rapid moves, disconnections, reconnections

# Test sequence:
# 1. All clients should see same initial state
# 2. Make moves rapidly from different clients
# 3. Disconnect one client (close browser tab)
# 4. Other clients should see "X disconnected" message
# 5. Reconnect client (refresh browser)
# 6. Should rejoin game and see current state
```

### Socket.IO event tests:
```javascript
// In browser console, test all events are handled:
const socket = window.socketService?.socket; // Access the socket instance

socket.on('game_state', (data) => console.log('Game state:', data));
socket.on('move_result', (data) => console.log('Move result:', data));
socket.on('player_disconnected', (data) => console.log('Player left:', data));
socket.on('player_reconnected', (data) => console.log('Player returned:', data));
socket.on('letters_drawn', (data) => console.log('Letters drawn:', data));
socket.on('game_ended', (data) => console.log('Game ended:', data));

// Then trigger these events using terminal client or server actions
```

### Edge case tests:
1. **Network interruption**: Disconnect wifi, reconnect
2. **Invalid moves**: Try words not in dictionary
3. **Game ending**: Use terminal client to end game
4. **Multiple browser tabs**: Open game in 2 tabs with same user

### Success criteria:
- All Socket.IO events properly handled and displayed
- Graceful handling of disconnections/reconnections
- Error messages shown for invalid moves
- Game state always consistent across clients

---

## Step 6: UI/UX Polish + Error Handling

### Accessibility tests:
```bash
# Test keyboard navigation
# Tab through all interactive elements
# Enter key should submit forms
# Escape key should clear input (if implemented)
```

### Error handling tests:
```javascript
// Test various error conditions:

// 1. Server down
// Stop your Python server, try to make moves

// 2. Invalid session token
localStorage.setItem('session_token', 'invalid');
// Refresh page, should handle gracefully

// 3. Game not found
// Try to join non-existent game ID

// 4. Network errors
// Use browser dev tools to simulate offline
```

### Visual tests:
- Test on different screen sizes (mobile, tablet, desktop)
- Test with different browsers (Chrome, Firefox, Safari)
- Test color contrast for accessibility
- Test with browser zoom at 150%, 200%

### Success criteria:
- Responsive design works on mobile
- Error messages are user-friendly
- Loading states are shown appropriately
- Graceful degradation when server is unavailable

---

## Automated Testing Setup (Optional but Recommended)

### Jest + React Testing Library tests:
```javascript
// components/__tests__/WordInput.test.js
import { render, fireEvent, screen } from '@testing-library/react';
import WordInput from '../WordInput';

test('submits word when form is submitted', () => {
  const onSubmitWord = jest.fn();
  render(<WordInput onSubmitWord={onSubmitWord} onPass={jest.fn()} />);
  
  const input = screen.getByPlaceholderText(/enter word/i);
  fireEvent.change(input, { target: { value: 'hello' } });
  fireEvent.submit(input.closest('form'));
  
  expect(onSubmitWord).toHaveBeenCalledWith('hello');
});
```

### End-to-end tests with Cypress:
```javascript
// cypress/integration/game_flow.spec.js
describe('Game Flow', () => {
  it('can create and join a game', () => {
    cy.visit('/');
    cy.get('[data-testid=username-input]').type('testuser');
    cy.get('[data-testid=login-button]').click();
    cy.get('[data-testid=create-game-button]').click();
    cy.get('[data-testid=game-list]').should('contain', 'Game');
  });
});
```

## Quick Validation Checklist

After each step, the developer should be able to answer "YES" to:

**Step 1**: ✅ React app starts, Socket.IO connects to server
**Step 2**: ✅ Can login and see authenticated state persisted
**Step 3**: ✅ Can create/list/join games via the UI
**Step 4**: ✅ Can make moves in web client that terminal client sees
**Step 5**: ✅ All real-time events work correctly across clients
**Step 6**: ✅ App handles errors gracefully and looks polished

This testing approach ensures each step builds correctly on the previous ones and maintains compatibility with your existing server implementation.
