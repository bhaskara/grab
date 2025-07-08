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


### 4. WebSocket Connection

#### `GET /api/games/{game_id}/connect`
Establishes a WebSocket connection for real-time game communication. This endpoint upgrades the HTTP connection to WebSocket.

**Headers:**
```
Authorization: Bearer <session_token>
Connection: Upgrade
Upgrade: websocket
Sec-WebSocket-Key: <client-generated-key>
Sec-WebSocket-Version: 13
```

**Response:**
- `101 Switching Protocols` - WebSocket connection established
- `401` - Invalid or missing session token
- `404` - Game not found
- `403` - Player not in this game
- `400` - Game not active or WebSocket upgrade failed

**Notes:**
- Player must have already joined the game via `POST /api/games/{game_id}/join`
- Game must be in "active" status
- WebSocket messages will be documented separately
- Connection is automatically closed if the game ends or player leaves

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

### WebSocket Lifecycle
- Automatically clean up WebSocket connections on game end
- Handle client disconnections gracefully
- Implement ping/pong for connection health monitoring
