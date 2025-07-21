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
- `connected` - Emitted when authentication succeeds
- `error` - Emitted for authentication or connection errors

---

#### **Socket.IO Events**

### **Client → Server Events**

#### **`join_game`**
Join a game room to receive real-time updates.

**Data:**
```json
{
  "game_id": "ABC123"
}
```

**Responses:**
- `game_state` - Current game state (on success)
- `error` - Error message if join fails

**Requirements:**
- Player must be authenticated
- Player must have already joined the game via HTTP API
- Game must be in "active" status

---

#### **`move`**
Send a move to the game.

**Data:**
```json
{
  "data": "move-string-specific-to-game-type"
}
```

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
    "game_type": "dummy",
    "status": "active",
    "current_turn": 1,
    "turn_time_remaining": null,
    "players": {
      "username1": {
        "connected": true,
        "score": 0,
        "ready_for_next_turn": false
      },
      "username2": {
        "connected": false,
        "score": 5,
        "ready_for_next_turn": true
      }
    },
    "state": "{\"game-specific-state-json\"}"
  }
}
```

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
