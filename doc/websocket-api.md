# Multi-Game WebSocket API Specification

## Overview
This WebSocket API provides real-time communication for multiplayer games, allowing players to make moves and receive game state updates. The API is designed to support multiple game types with game-specific logic handled by dedicated game classes. The WebSocket connection is established after a player has joined a game through the HTTP API and the game is in "active" status.

## Connection Establishment

### WebSocket Endpoint
```
GET /api/games/{game_id}/connect
```

### Prerequisites
- Player must be authenticated with a valid JWT session token
- Player must have already joined the game via `POST /api/games/{game_id}/join`
- Game must be in "active" status

### Connection Headers
```
Authorization: Bearer <session_token>
Connection: Upgrade
Upgrade: websocket
Sec-WebSocket-Key: <client-generated-key>
Sec-WebSocket-Version: 13
```

### Connection Response
- **101 Switching Protocols** - WebSocket connection established successfully
- **401** - Invalid or missing session token
- **404** - Game not found
- **403** - Player not in this game
- **400** - Game not active or WebSocket upgrade failed

### Client-Side Connection Example
```javascript
const gameId = "ABC123";
const sessionToken = localStorage.getItem('session_token');

const ws = new WebSocket(
    `ws://localhost:5000/api/games/${gameId}/connect`,
    [], // protocols
    {
        headers: {
            'Authorization': `Bearer ${sessionToken}`
        }
    }
);
```

## Message Format

All WebSocket messages are JSON-encoded strings. The connection uses bidirectional communication with different message types for client-to-server and server-to-client communication.

### Message Envelope
All messages follow a consistent structure:

```json
{
    "type": "message_type",
    "data": "message_payload_or_object"
}
```

## Client-to-Server Messages

### 1. Make Move
Attempts to make a game move. The move format is game-specific.

**Message:**
```json
{
    "type": "move",
    "data": "HELLO"
}
```

**Parameters:**
- `data` (string): The move the player wants to make. The format and validation of this string is determined by the specific game type. Examples:
  - Word games: `"HELLO"` (word to create)
  - Board games: `"e2-e4"` (chess notation)
  - Card games: `"play:ace_spades"` (card to play)
  - The server's game-specific logic will validate if this move is legal in the current game state.

### 2. Request Game Status
Requests the current complete game state.

**Message:**
```json
{
    "type": "get_status"
}
```

**Notes:**
- Useful for initial state retrieval after connection or after reconnection
- Server will respond with a `game_state` message

### 3. Player Actions
Non-move actions that affect game flow.

**Message:**
```json
{
    "type": "player_action",
    "data": "action_name"
}
```

**Supported Actions:**
- `"ready_for_next_turn"` - Indicates player cannot make any more words this turn
- `"pause_request"` - Requests to pause the game (implementation dependent)
- `"resume_request"` - Requests to resume a paused game (implementation dependent)

## Server-to-Client Messages

### 1. Move Result
Response to a player's move attempt, sent only to the player who made the move.

**Successful Move:**
```json
{
    "type": "move_result",
    "success": true,
    "game_state": {
        // Complete game state object (see Game State Format below)
    }
}
```

**Failed Move:**
```json
{
    "type": "move_result", 
    "success": false,
    "error": "Invalid word: HELLO cannot be formed with available tiles"
}
```

### 2. Game State Update
Broadcast to all players when the game state changes (due to moves by other players, turn progression, etc.).

**Message:**
```json
{
    "type": "game_state",
    "data": {
        // Complete game state object (see Game State Format below)
    }
}
```

### 3. Game Events
Notifications about game progression and special events.

**Turn End:**
```json
{
    "type": "turn_ended",
    "reason": "timeout|all_players_ready",
    "next_turn_starts_in": 3000
}
```

**Game End:**
```json
{
    "type": "game_ended",
    "reason": "game_complete|manual_stop|timeout",
    "final_scores": {
        "player1": 150,
        "player2": 120
    },
    "winner": "player1"
}
```

**Player Connection Events:**
```json
{
    "type": "player_disconnected",
    "player": "username"
}
```

```json
{
    "type": "player_reconnected", 
    "player": "username"
}
```

### 4. Error Messages
General errors not related to move attempts.

**Message:**
```json
{
    "type": "error",
    "message": "Connection error or general game error description"
}
```

## Game State Format

The game state object contains game-independent information and a game-specific state string:

```json
{
    "game_id": "ABC123",
    "game_type": "grab",
    "status": "active",
    "current_turn": 15,
    "turn_time_remaining": 45000,
    "players": {
        "alice": {
            "connected": true,
            "score": 150,
            "ready_for_next_turn": false
        },
        "bob": {
            "connected": true,
            "score": 120,
            "ready_for_next_turn": true
        }
    },
    "state": "{\"pool\":[{\"letter\":\"R\",\"points\":1}],\"tiles_remaining\":67,\"words\":{\"alice\":[{\"word\":\"HELLO\",\"points\":8}]}}"
}
```

### Game-Independent Fields

- `game_id` (string): Unique identifier for this game
- `game_type` (string): Type of game being played (e.g., "grab", "chess", "poker")
- `status` (string): Current game status ("active", "paused", "finished")
- `current_turn` (integer): Turn number (starts at 1)
- `turn_time_remaining` (integer): Milliseconds remaining in current turn (null if no time limit)
- `players` (object): Map of player usernames to their connection and basic state
- `state` (string): Game-specific state as a JSON-encoded string

### Player State Fields (Game-Independent)

- `connected` (boolean): Whether the player is currently connected
- `score` (integer): Current total score for this player
- `ready_for_next_turn` (boolean): Whether player has indicated they're done with this turn

### Game-Specific State

The `state` field contains a JSON-encoded string with all game-specific information. This string should be parsed by game-specific client code. Examples:

**Grab Game State:**
```json
{
    "pool": [
        {"letter": "R", "points": 1},
        {"letter": "S", "points": 1}
    ],
    "tiles_remaining": 67,
    "words": {
        "alice": [
            {"word": "HELLO", "tiles": [...], "points": 8}
        ],
        "bob": [
            {"word": "GRAB", "tiles": [...], "points": 7}
        ]
    }
}
```

**Chess Game State:**
```json
{
    "board": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
    "active_color": "white",
    "castling": "KQkq",
    "en_passant": "-",
    "halfmove_clock": 0,
    "fullmove_number": 1
}
```

**Card Game State:**
```json
{
    "deck_size": 45,
    "hands": {
        "alice": {"card_count": 7, "cards": ["hidden", "hidden", ...]},
        "bob": {"card_count": 6, "cards": ["hidden", "hidden", ...]}
    },
    "table": [
        {"card": "ace_spades", "played_by": "alice"}
    ]
}
```

## Connection Lifecycle

### 1. Initial Connection
```
Client connects → Server validates → Server sends initial game_state
```

### 2. Normal Gameplay
```
Client sends move → Server validates → Server sends move_result to sender + game_state to all players
```

### 3. Turn Progression
```
Timer expires OR all players ready → Server sends turn_ended → Server adds new tile → Server sends game_state
```

### 4. Disconnection/Reconnection
```
Client disconnects → Server marks player as disconnected → Server broadcasts player_disconnected
Client reconnects → Server validates → Server marks player as connected → Server sends current game_state → Server broadcasts player_reconnected
```

### 5. Game End
```
Game ends → Server sends game_ended → Server closes all connections for this game
```

## Error Handling

### Client-Side Error Handling
```javascript
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    switch (message.type) {
        case 'move_result':
            if (message.success) {
                updateGameDisplay(message.game_state);
                showMoveSuccess();
            } else {
                showMoveError(message.error);
            }
            break;
            
        case 'game_state':
            updateGameDisplay(message.data);
            break;
            
        case 'error':
            showGeneralError(message.message);
            break;
            
        case 'game_ended':
            showGameResults(message.final_scores, message.winner);
            break;
    }
};

ws.onerror = (error) => {
    showConnectionError("WebSocket connection error");
};

ws.onclose = (event) => {
    if (event.wasClean) {
        showMessage("Game ended normally");
    } else {
        attemptReconnection();
    }
};
```

### Server-Side Error Conditions

**Invalid move formats:**
- Empty or non-string move data
- Move data that doesn't conform to the game's expected format
- Moves that are not legal according to game-specific rules

**Connection issues:**
- Player not authenticated
- Player not in the specified game
- Game not in active status
- Malformed JSON messages

**Game state issues:**
- Game has ended
- Player disconnected during move
- Concurrent move conflicts

## Implementation Notes

### Concurrency
- Server must handle concurrent moves from multiple players safely
- Use appropriate locking mechanisms for game state modifications
- Moves should be processed atomically (all or nothing)

### Performance
- Send complete game state rather than deltas for simplicity
- Game-specific state is JSON-encoded as a string to allow flexibility
- Consider message compression for large game states if needed
- Implement reasonable rate limiting for move attempts

### Security
- Validate all incoming messages against expected schemas
- Ensure players can only make moves for games they've joined
- Sanitize and validate move inputs before processing (game-specific validation)
- Game-specific state parsing should be done safely to prevent injection attacks

### Reconnection Support
- Maintain player state even when disconnected
- Allow graceful reconnection with state restoration
- Consider implementing connection heartbeat/ping mechanism

### Testing
- Test WebSocket connections with multiple concurrent players
- Verify proper error handling for all failure scenarios
- Test reconnection scenarios and edge cases
- Validate that all players receive consistent game state updates
- Test with multiple game types to ensure the generic API works correctly
- Verify game-specific state parsing and validation