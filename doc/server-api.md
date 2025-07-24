# Grab Game Server HTTP API Specification

## Overview
This HTTP API manages user sessions, game lifecycle, and WebSocket connection establishment for the Grab game server. All endpoints return JSON responses unless otherwise specified.

## Base URL
All endpoints are relative to the server base URL (e.g., `http://localhost:5000`)

## Common Response Format
```json
{
  "success": true|false,
  "data": {...},
  "error": "error message if success=false"
}
```

## Endpoints

### 1. Player Authentication

#### `POST /api/auth/login`
Authenticates a player with just a username (no password required).

**Request Body:**
```json
{
  "username": "string (required, 1-50 chars, alphanumeric + underscore)"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "player_id": "uuid-string",
    "username": "string",
    "session_token": "jwt-token-string"
  }
}
```

**Errors:**
- `400` - Invalid username format or missing username
- `409` - Username already taken by an active session

**Notes:**
- Returns a JWT session token that must be included in subsequent requests
- Session tokens expire after 24 hours of inactivity
- If a username is already taken, the client should prompt for a different name

---

### 2. Game Management

#### `POST /api/games`
Creates a new game. Requires authentication.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Request Body:**
```json
{
  "max_players": 4,  // optional, defaults to 4
  "time_limit_seconds": 300  // optional, defaults to 300 (5 minutes per turn)
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "game_id": "alphanumeric-string",
    "creator_id": "uuid-string",
    "status": "waiting",  // waiting, active, finished
    "max_players": 4,
    "time_limit_seconds": 300,
    "created_at": "2025-06-11T10:30:00Z"
  }
}
```

**Errors:**
- `401` - Invalid or missing session token
- `400` - Invalid game parameters

---

#### `GET /api/games`
Gets information about all games on the server.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "games": [
      {
        "game_id": "ABC123",
        "status": "waiting|active|finished",
        "max_players": 4,
        "current_players": [
          {
            "player_id": "uuid-string",
            "username": "string",
            "joined_at": "2025-06-11T10:31:00Z"
          }
        ],
        "creator_id": "uuid-string",
        "created_at": "2025-06-11T10:30:00Z",
        "started_at": "2025-06-11T10:32:00Z",  // null if not started
        "finished_at": "2025-06-11T10:45:00Z"  // null if not finished
      }
    ],
    "total_games": 1
  }
}
```

**Errors:**
- `401` - Invalid or missing session token

---

#### `GET /api/games/{game_id}`
Gets information about a specific game.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "game_id": "ABC123",
    "status": "waiting|active|finished",
    "max_players": 4,
    "current_players": [
      {
        "player_id": "uuid-string",
        "username": "string",
        "joined_at": "2025-06-11T10:31:00Z"
      }
    ],
    "creator_id": "uuid-string",
    "created_at": "2025-06-11T10:30:00Z",
    "started_at": "2025-06-11T10:32:00Z",  // null if not started
    "finished_at": "2025-06-11T10:45:00Z"  // null if not finished
  }
}
```

**Errors:**
- `401` - Invalid or missing session token
- `404` - Game not found

---

#### `POST /api/games/{game_id}/start`
Starts a game that is currently waiting for players. Only the game creator can start the game.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "game_id": "ABC123",
    "status": "active",
    "started_at": "2025-06-11T10:32:00Z"
  }
}
```

**Errors:**
- `401` - Invalid or missing session token
- `403` - Only the game creator can start the game
- `404` - Game not found
- `400` - Game cannot be started (wrong status, not enough players, etc.)

---

#### `DELETE /api/games/{game_id}`
Stops/cancels a game. Only the game creator can stop the game.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "game_id": "ABC123",
    "status": "finished",
    "finished_at": "2025-06-11T10:35:00Z"
  }
}
```

**Errors:**
- `401` - Invalid or missing session token
- `403` - Only the game creator can stop the game
- `404` - Game not found

---

### 3. Player-Game Association

#### `POST /api/games/{game_id}/join`
Adds the authenticated player to a game.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "game_id": "ABC123",
    "player_id": "uuid-string",
    "joined_at": "2025-06-11T10:31:00Z"
  }
}
```

**Errors:**
- `401` - Invalid or missing session token
- `404` - Game not found
- `400` - Game is full, already started, or player already in game
- `409` - Player is already in another active game

---


### 4. Socket.IO Real-Time Communication

The server uses **Socket.IO** for real-time communication instead of standard WebSocket. This provides better reliability with automatic reconnection, fallback protocols, and event-based messaging.

**Socket.IO Benefits:**
- **Automatic Reconnection** - Clients reconnect automatically with exponential backoff
- **Protocol Fallback** - Falls back to long-polling if WebSocket is unavailable
- **Event System** - Named events instead of raw message parsing
- **Room Management** - Built-in support for broadcasting to game rooms  
- **Connection Health** - Automatic ping/pong and connection monitoring

#### **Socket.IO Connection**

**JavaScript/Browser:**
```javascript
const socket = io('http://localhost:5000', {
  auth: {
    token: 'jwt-session-token-here'
  }
});
```

**Python Client:**
```python
import socketio

sio = socketio.Client()
sio.connect('http://localhost:5000', auth={'token': 'jwt-session-token-here'})
```

**Authentication:**
- Include JWT session token in `auth.token` field during connection
- Token can also be provided via query parameter: `?token=jwt-session-token`
- Connection will be rejected if token is invalid or missing

**Connection Events:**
- `connected` - Emitted when authentication succeeds (includes initial game state if player is in an active game)
- `error` - Emitted for authentication or connection errors

**Automatic Game Room Joining:**
- Upon successful authentication, if the player is in an active game, they are automatically joined to that game's Socket.IO room
- No separate `join_game` event is required
- Players immediately begin receiving `game_state` updates for their active game

---

#### **Client Integration Patterns**

**Complete JavaScript Client Example:**
```javascript
class GrabGameClient {
  constructor(serverUrl, sessionToken) {
    this.socket = io(serverUrl, {
      auth: { token: sessionToken },
      autoConnect: false
    });
    
    this.setupEventHandlers();
  }
  
  setupEventHandlers() {
    this.socket.on('connected', (data) => {
      console.log('Connected to server:', data.message);
    });
    
    this.socket.on('game_state', (data) => {
      this.updateGameUI(data.data);
    });
    
    this.socket.on('move_result', (data) => {
      if (data.success) {
        console.log('Move successful');
        this.updateGameUI(data.game_state);
      } else {
        this.showError(data.error);
      }
    });
    
    this.socket.on('player_disconnected', (data) => {
      this.showPlayerStatus(data.player, 'disconnected');
    });
    
    this.socket.on('player_reconnected', (data) => {
      this.showPlayerStatus(data.player, 'reconnected');
    });
    
    this.socket.on('error', (data) => {
      this.showError(data.message);
    });
    
    this.socket.on('disconnect', (reason) => {
      console.log('Disconnected:', reason);
      this.showConnectionStatus('disconnected');
    });
  }
  
  connect() {
    this.socket.connect();
  }
  
  makeMove(word) {
    this.socket.emit('move', { data: word });
  }
  
  passMove() {
    this.socket.emit('player_action', { data: 'ready_for_next_turn' });
  }
  
  getGameStatus() {
    this.socket.emit('get_status');
  }
  
  updateGameUI(gameState) {
    // Update your UI with the new game state
    document.getElementById('pool-letters').textContent = 
      this.formatLetterPool(gameState.state.pool);
    
    // Update player scores
    Object.entries(gameState.players).forEach(([username, playerData]) => {
      const scoreElement = document.getElementById(`score-${username}`);
      if (scoreElement) {
        scoreElement.textContent = playerData.score;
      }
    });
    
    // Update player words
    const state = JSON.parse(gameState.state);
    state.words_per_player.forEach((words, playerIndex) => {
      const wordsElement = document.getElementById(`words-player-${playerIndex}`);
      if (wordsElement) {
        wordsElement.textContent = words.join(', ');
      }
    });
  }
  
  formatLetterPool(poolArray) {
    // Convert [1, 0, 2, 0, 1, ...] to "a c c e"
    const letters = [];
    poolArray.forEach((count, index) => {
      const letter = String.fromCharCode(97 + index); // 'a' + index
      for (let i = 0; i < count; i++) {
        letters.push(letter);
      }
    });
    return letters.join(' ');
  }
  
  showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    
    // Hide error after 5 seconds
    setTimeout(() => {
      errorDiv.style.display = 'none';
    }, 5000);
  }
}

// Usage
const sessionToken = localStorage.getItem('session_token');
const client = new GrabGameClient('http://localhost:5000', sessionToken);

client.connect();
// Player is automatically joined to their active game's room upon connection

// Handle form submission for word input
document.getElementById('word-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const wordInput = document.getElementById('word-input');
  const word = wordInput.value.trim().toLowerCase();
  
  if (word) {
    client.makeMove(word);
    wordInput.value = '';
  }
});

// Handle pass button
document.getElementById('pass-button').addEventListener('click', () => {
  client.passMove();
});
```

**Connection Management Best Practices:**
- Always handle reconnection scenarios gracefully
- Store game state locally to survive disconnections
- Show clear UI feedback for connection status
- Implement exponential backoff for manual reconnection attempts
- Handle authentication token expiration

**Error Handling Patterns:**
- Display user-friendly error messages for invalid moves
- Distinguish between temporary (network) and permanent (game logic) errors
- Provide recovery suggestions where appropriate
- Log detailed errors for debugging while showing simple messages to users

---

#### **Socket.IO Events**

### **Client → Server Events**


#### **`move`**
Send a move to the game.

**Data:**
```json
{
  "data": "word-to-make"
}
```

**Move Format:**
- **Word Move**: Send a string containing the word you want to make (e.g., `"hello"`)

**Word Making Requirements:**
- Word must be in the allowed dictionary (TWL06 or SOWPODS)
- Word must be constructible from available letters in the pool and existing player words
- Only one existing word can be used per move (from any player)
- Used words are removed from their original owner and the new word goes to the current player

**Responses:**
- `move_result` - Success/failure with updated game state
- `game_state` - Broadcast to all players in the game (on success)

**Response Format:**
```json
{
  "success": true|false,
  "error": "error-message-if-failed",
  "game_state": { ... }  // Only on success
}
```

**Common Move Errors:**
- `"Word 'xyz' is not in the allowed word list"`
- `"Cannot construct word 'xyz' with available letters and words"`
- `"Player X is out of range (0-Y)"`

---

#### **`get_status`**
Request current game state.

**Data:** None

**Response:**
- `game_state` - Current game state
- `error` - If not in a game or other error

---

#### **`player_action`**
Send non-move actions to the game.

**Data:**
```json
{
  "data": "action-type"
}
```

**Supported Actions:**
- `"ready_for_next_turn"` - Signal ready to proceed to next turn

**Response:**
- `game_state` - Broadcast to all players (on success)
- `error` - If action fails

---

### **Server → Client Events**

#### **`game_state`**
Current game state broadcast to all players.

**Data:**
```json
{
  "data": {
    "game_id": "ABC123",
    "game_type": "grab|dummy",
    "status": "waiting|active|finished",
    "current_turn": 1,
    "turn_time_remaining": null,
    "players": {
      "username1": {
        "connected": true,
        "score": 15,
        "ready_for_next_turn": false
      },
      "username2": {
        "connected": false,
        "score": 23,
        "ready_for_next_turn": true
      }
    },
    "state": "{\"grab-game-state-json\"}"
  }
}
```

**Game State Details:**

**For Grab Games (`game_type`: `"grab"`):**
The `state` field contains JSON with the following structure:
```json
{
  "num_players": 2,
  "pool": [1, 0, 2, 0, 1, 0, ...],  // 26-element array of letter counts (a-z)
  "bag": [8, 2, 0, 4, 11, 2, ...],   // 26-element array of remaining letters
  "words_per_player": [
    ["hello", "cat"],   // Player 0's words
    ["world", "dog"]    // Player 1's words
  ],
  "scores": [15, 23],     // Current scores for each player
  "passed": [false, true] // Whether each player has passed since last letter draw
}
```

**Letter Pool/Bag Format:**
- Arrays of 26 integers representing letter counts where index 0 = 'a', index 1 = 'b', etc.
- Pool contains letters currently available for making words
- Bag contains letters not yet drawn from the tile bag

**Player Words:**
- Each player has a list of word strings they currently own
- Words can be taken by other players to form new words

**For Dummy Games (`game_type`: `"dummy"`):**
The `state` field contains simpler JSON for testing purposes.

---

#### **`move_result`**
Response to a move attempt.

**Data:**
```json
{
  "success": true|false,
  "error": "error-message-if-failed",
  "game_state": { ... }  // Game state object (only on success)
}
```

---

#### **`player_disconnected`**
Broadcast when a player disconnects.

**Data:**
```json
{
  "player": "username"
}
```

---

#### **`player_reconnected`**
Broadcast when a player reconnects.

**Data:**
```json
{
  "player": "username"
}
```

---

#### **`connected`**
Sent to client after successful authentication.

**Data:**
```json
{
  "message": "Successfully connected"
}
```

---

#### **`error`**
Error messages for various failures.

**Data:**
```json
{
  "message": "error-description"
}
```

**Common Errors:**
- `"Authentication token required"`
- `"Invalid or expired token"`
- `"Not authenticated"`
- `"Game not found"`
- `"Player not in this game"`
- `"Game is not active"`
- `"Not in a game"`

**Move-Specific Errors:**
- `"Word 'xyz' is not in the allowed word list"`
- `"Cannot construct word 'xyz' with available letters and words"`
- `"Player X is out of range (0-Y)"`
- `"Word contains invalid character: 'X'. Only letters 'a' to 'z' are allowed"`

**Connection Errors:**
- `"Player disconnected unexpectedly"`
- `"Connection timeout"`
- `"Maximum reconnection attempts exceeded"`

**Game State Errors:**
- `"Game has ended"`
- `"Not your turn"`
- `"All players have already passed this turn"`

---

## Implementation Notes

### Session Management
- Use JWT tokens for stateless authentication
- Include player_id and username in JWT payload
- Tokens should be validated on every authenticated request

### Game ID Generation

- Ensure uniqueness across active games
- Case-insensitive for user entry

### Error Handling
- Always return proper HTTP status codes
- Include descriptive error messages in the response body
- Log errors server-side for debugging

### Concurrency
- Handle concurrent requests to join/leave games safely
- Prevent race conditions when starting games or checking capacity
- Use appropriate locking mechanisms for game state modifications

### Socket.IO Lifecycle
- Automatic reconnection with exponential backoff on client disconnections
- Graceful handling of player disconnections with notifications to other players
- Built-in ping/pong for connection health monitoring
- Automatic cleanup of connections when games end or players leave
- Players are automatically removed from game rooms on disconnection

### Turn Timers and Game Progression

**Turn Timer Implementation:**
- Games can be configured with `time_limit_seconds` (default: 300 seconds/5 minutes per turn)
- Timer starts when a new letter is drawn and all players' `passed` status is reset to false
- When timer expires, game automatically draws the next letter (if available) or ends the game
- `turn_time_remaining` field in `game_state` shows seconds remaining (null if no active timer)

**Game Progression Events:**

#### **`turn_starting`**
Broadcast when a new turn begins (new letter drawn).

**Data:**
```json
{
  "turn_number": 2,
  "letters_drawn": ["e"],
  "time_limit": 300,
  "letters_remaining_in_bag": 85
}
```

#### **`turn_ending`**
Broadcast when all players have passed or time limit is reached.

**Data:**
```json
{
  "turn_number": 1,
  "reason": "all_players_passed|time_expired",
  "final_moves_count": 3
}
```

#### **`game_ending`**
Broadcast when the game is about to end (no letters left in bag).

**Data:**
```json
{
  "reason": "bag_empty|creator_stopped",
  "final_scores": {
    "player1": 45,
    "player2": 38
  },
  "winner": "player1"
}
```

**Turn Timer Behavior:**
- Timer is paused when no players are connected
- Timer resumes when at least one player reconnects
- If all players disconnect for more than 10 minutes, game is automatically ended
- Players receive `game_state` updates every 30 seconds with updated `turn_time_remaining`

**Automatic Game Progression:**
1. When all players pass → Draw next letter (if available) or end game
2. When turn timer expires → Same as all players passing (not implemented ATM)
3. When bag is empty → Game ends, bonus scores calculated
4. When game creator stops game → Game ends immediately

**Game End Scoring:**
- Each player receives bonus points equal to the total value of words they still own
- Final `game_state` event includes updated scores with bonuses applied
- Game status changes to "finished"
