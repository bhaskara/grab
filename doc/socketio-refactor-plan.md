# Socket.IO-First Implementation Plan

## Overview

This plan refactors the Grab game server to require Socket.IO WebSocket connections before players can join games. This simplifies the codebase by eliminating race conditions and complex dual-path logic between HTTP and WebSocket APIs.

## Current Problem

The existing code tries to handle multiple connection orders:
1. Socket.IO connects first, then HTTP join
2. HTTP join first, then Socket.IO connects
3. Simultaneous connections

This creates complexity, race conditions, and hard-to-debug edge cases.

## Solution

Enforce a simple, reliable flow:
1. Player authenticates via HTTP (gets JWT token)
2. Player establishes Socket.IO connection with JWT token
3. Player joins games via HTTP (requires active Socket.IO connection)
4. All real-time communication happens via Socket.IO

## Implementation Steps

### Step 1: Update WebSocket Handlers (websocket_handlers.py)

#### 1.1 Simplify `handle_connect` function

**Location:** `src/grab/websocket_handlers.py`, `handle_connect` function

**Current code** has complex auto-join logic. **Replace with:**

```python
@socketio.on('connect')
def handle_connect(auth):
    """Handle WebSocket connection with authentication only."""
    try:
        # Get token from auth data or query parameters
        token = None
        if auth and 'token' in auth:
            token = auth['token']
        elif 'token' in request.args:
            token = request.args.get('token')
        
        if not token:
            emit('error', {'message': 'Authentication token required'})
            return False
        
        # Verify token
        payload = verify_session_token(token)
        if not payload:
            emit('error', {'message': 'Invalid or expired token'})
            return False
        
        # Store player connection info (no game_id yet)
        username = payload['username']
        connected_players[request.sid] = {
            'player_id': payload['player_id'],
            'username': username,
            'game_id': None  # Will be set when they join a game via HTTP
        }
        
        # Simple success response
        emit('connected', {
            'message': 'Successfully connected',
            'username': username
        })
        
        logger.info(f"Player '{username}' connected via Socket.IO")
        
    except Exception as e:
        emit('error', {'message': f'Connection error: {str(e)}'})
        return False
```

**What to remove:**
- All auto-join game logic (the `try/except` block that checks `game_server.get_player_game()`)
- The complex reconnection notifications
- Initial game state sending

#### 1.2 Update `handle_disconnect` function

**Location:** Same file, `handle_disconnect` function

**Simplify to:**

```python
@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    if request.sid in connected_players:
        player_info = connected_players[request.sid]
        game_id = player_info.get('game_id')
        username = player_info['username']
        
        if game_id:
            # Notify other players in the game
            socketio.emit('player_disconnected', 
                         {'player': username},
                         room=game_id)
            
            # Remove from game room tracking
            if game_id in game_rooms:
                game_rooms[game_id].discard(request.sid)
                logger.info(f"Player '{username}' removed from game room {game_id}")
        
        # Remove from connected players
        del connected_players[request.sid]
        logger.info(f"Player '{username}' disconnected from Socket.IO")
```

#### 1.3 Remove unused functions

**Remove completely:**
- `handle_join_game_room` function (no longer needed)

### Step 2: Update HTTP API (api.py)

#### 2.1 Modify `join_game` function

**Location:** `src/grab/api.py`, `join_game` function

**Find this section:**
```python
# Check that WebSocket server is available
if not socketio_instance:
    return jsonify({'success': False, 'error': 'WebSocket server not initialized'}), 500

# Check for testing flag to skip WebSocket requirement
data = request.get_json() or {}
skip_websocket_check = data.get('skip_websocket_check', False)

# Check that player is connected via Socket.IO (required for real-time gameplay)
from .websocket_handlers import get_connected_player_socket_id, connected_players, game_rooms
socket_id = get_connected_player_socket_id(username)
if not socket_id and not skip_websocket_check:
    return jsonify({'success': False, 'error': 'Player must be connected via WebSocket to join game'}), 400
```

**Replace with:**
```python
# Require active WebSocket connection (no exceptions)
if not socketio_instance:
    return jsonify({'success': False, 'error': 'WebSocket server not initialized'}), 500

from .websocket_handlers import get_connected_player_socket_id, connected_players, game_rooms
socket_id = get_connected_player_socket_id(username)
if not socket_id:
    return jsonify({
        'success': False, 
        'error': 'Active WebSocket connection required. Please connect via Socket.IO first.'
    }), 400
```

#### 2.2 Simplify the room joining logic

**Find this section:**
```python
# Update player's game_id in connected_players for WebSocket handlers (if connected)
if socket_id:
    connected_players[socket_id]['game_id'] = game_id
    
    print(f"[DEBUG] HTTP join: Attempting to join socket {socket_id} (player {username}) to room {game_id}")
    
    # Check if we're in testing mode
    is_testing = current_app.config.get('TESTING', False)
    
    # Use the socketio instance's server to join the room directly
    try:
        socketio_instance.server.enter_room(socket_id, game_id)
    except ValueError as e:
        if "sid is not connected to requested namespace" in str(e) and is_testing:
            print(f"[DEBUG] HTTP join: Socket {socket_id} not connected to namespace (testing mode)")
            # In testing, socket may not be connected yet - this is acceptable
        else:
            raise
    else:
        # Only do room tracking and state sending if enter_room succeeded
        # Add to game room tracking
        if game_id not in game_rooms:
            game_rooms[game_id] = set()
        game_rooms[game_id].add(socket_id)
        
        print(f"[DEBUG] HTTP join: Socket {socket_id} joined room {game_id}, room now has {len(game_rooms[game_id])} members")
        
        # Send initial game state to the player
        try:
            from .websocket_handlers import _get_game_state
            game_state = _get_game_state(game_id)
            socketio_instance.emit('game_state', {'data': game_state}, room=socket_id)
        except Exception as e:
            print(f"[DEBUG] Failed to send initial game state: {e}")
```

**Replace with:**
```python
# We know socket_id exists (checked above), so this will work
connected_players[socket_id]['game_id'] = game_id

# Join Socket.IO room (guaranteed to work since we verified connection)
socketio_instance.server.enter_room(socket_id, game_id)

# Add to game room tracking
if game_id not in game_rooms:
    game_rooms[game_id] = set()
game_rooms[game_id].add(socket_id)

logger.info(f"Player '{username}' joined Socket.IO room {game_id} (room size: {len(game_rooms[game_id])})")

# Send initial game state to the player
try:
    from .websocket_handlers import _get_game_state
    game_state = _get_game_state(game_id)
    socketio_instance.emit('game_state', {'data': game_state}, room=socket_id)
    logger.info(f"Sent initial game state to player '{username}'")
except Exception as e:
    logger.error(f"Failed to send initial game state to {username}: {e}")
    # Don't fail the join, but log the error
```

### Step 3: Update Tests

#### 3.1 Remove skip_websocket_check from tests

**Location:** `tests/test_api.py`

**Find all instances of:**
```python
json={'skip_websocket_check': True}
```

**Replace with actual Socket.IO connections in tests.**

#### 3.2 Update test helper functions

**Add to test files that need WebSocket connections:**

```python
def create_test_socketio_connection(app, auth_headers):
    """Helper to create Socket.IO connection for testing."""
    # Extract token from auth headers
    token = auth_headers['Authorization'].split(' ')[1]
    
    # Create test Socket.IO client
    sio_client = app.socketio.test_client(app)
    sio_client.connect(auth={'token': token})
    
    # Wait for connection confirmation
    received = sio_client.get_received()
    connected_msg = None
    for msg in received:
        if msg['name'] == 'connected':
            connected_msg = msg
            break
    
    assert connected_msg is not None, "Failed to establish Socket.IO connection"
    return sio_client
```

#### 3.3 Update existing tests

**Example pattern for updating join tests:**

```python
def test_join_game_success(self, client, auth_headers, app):
    """Test successful game join with Socket.IO connection."""
    # Create a game
    create_response = client.post('/api/games', json={}, headers=auth_headers)
    game_id = json.loads(create_response.data)['data']['game_id']
    
    # Establish Socket.IO connection FIRST
    sio_client = create_test_socketio_connection(app, auth_headers)
    
    # Now join the game (this will work)
    response = client.post(f'/api/games/{game_id}/join', headers=auth_headers)
    assert response.status_code == 200
    
    # Verify we receive game state via Socket.IO
    received = sio_client.get_received()
    game_state_msg = None
    for msg in received:
        if msg['name'] == 'game_state':
            game_state_msg = msg
            break
    
    assert game_state_msg is not None
```

### Step 4: Update Client Scripts

#### 4.1 Update socketio_client.py

**Location:** `scripts/socketio_client.py`

**Modify the main connection flow in the `main()` function:**

```python
def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python socketio_client.py SERVER_URL")
        sys.exit(1)
    
    server_url = sys.argv[1]
    client = GrabSocketIOClient(server_url)
    
    # Login via HTTP first
    username = input("Enter your username: ").strip()
    if not username:
        print("Username cannot be empty")
        sys.exit(1)
    
    if not client.login(username):
        sys.exit(1)
    
    # Connect Socket.IO BEFORE showing menu
    if not client.connect_socketio():
        print("Failed to establish WebSocket connection. Cannot join games.")
        sys.exit(1)
    
    print("\n✅ Connected and ready!")
    print("\nAvailable commands:")
    print("  create - Create a new game")
    print("  join <game_id> - Join a game")
    print("  list - List all games")
    print("  exit - Exit the program")
    
    # Rest of main loop...
```

#### 4.2 Update api_driver.py

**Location:** `scripts/api_driver.py`

**Add WebSocket requirement check in the main loop:**

```python
# Add after login success:
print("⚠️  Note: This script requires Socket.IO for real-time gameplay.")
print("Use socketio_client.py for full functionality, or ensure WebSocket connection is established.")
```

### Step 5: Update Documentation

#### 5.1 Update API documentation

**Location:** `doc/server-api.md`

**In the `/api/games/{game_id}/join` section, update the description:**

```markdown
#### `POST /api/games/{game_id}/join`
Adds the authenticated player to a game.

**Prerequisites:**
- Player must be authenticated with a valid JWT session token
- Player must have an active Socket.IO WebSocket connection to the server

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
- `400` - Active WebSocket connection required
- `400` - Game is full, already started, or player already in game
- `409` - Player is already in another active game
```

#### 5.2 Add connection flow documentation

**Create new section in API docs:**

```markdown
## Required Connection Flow

For reliable real-time gameplay, clients must follow this connection sequence:

1. **Authenticate via HTTP:**
   ```javascript
   const response = await fetch('/api/auth/login', {
     method: 'POST',
     body: JSON.stringify({username: 'player1'})
   });
   const {session_token} = response.data;
   ```

2. **Establish Socket.IO connection:**
   ```javascript
   const socket = io('http://localhost:5000', {
     auth: {token: session_token}
   });
   
   await new Promise(resolve => {
     socket.on('connected', resolve);
   });
   ```

3. **Join games via HTTP:**
   ```javascript
   const response = await fetch(`/api/games/${gameId}/join`, {
     method: 'POST',
     headers: {Authorization: `Bearer ${session_token}`}
   });
   ```

4. **Receive real-time updates via Socket.IO:**
   ```javascript
   socket.on('game_state', (data) => {
     // Handle game state updates
   });
   ```

**Important:** Attempting to join a game without an active Socket.IO connection will result in a 400 error.
```

### Step 6: Testing and Validation

#### 6.1 Manual testing checklist

1. **Test normal flow:**
   - [ ] Login via HTTP returns JWT token
   - [ ] Socket.IO connection with token succeeds
   - [ ] Game join succeeds and sends game state
   - [ ] Real-time updates work during gameplay

2. **Test error cases:**
   - [ ] Joining game without Socket.IO connection returns 400 error
   - [ ] Socket.IO connection with invalid token fails
   - [ ] Socket.IO connection without token fails

3. **Test edge cases:**
   - [ ] Socket.IO disconnect during gameplay notifies other players
   - [ ] Reconnection after disconnect works properly
   - [ ] Multiple clients can join same game

#### 6.2 Automated testing

Run the full test suite:
```bash
pytest tests/ -v
```

Expected changes:
- Some tests may need updates to establish Socket.IO connections
- Tests using `skip_websocket_check` will need refactoring
- All WebSocket-related tests should pass

### Step 7: Cleanup

#### 7.1 Remove unused code

After implementation and testing:

1. **Remove from api.py:**
   - `skip_websocket_check` logic
   - Complex error handling for missing Socket.IO connections

2. **Remove from websocket_handlers.py:**
   - Auto-join logic in `handle_connect`
   - `handle_join_game_room` function

3. **Remove from tests:**
   - All `skip_websocket_check` usage
   - Obsolete test patterns

#### 7.2 Update logging

Add appropriate log levels:
- `INFO` for successful connections and joins
- `WARNING` for connection failures
- `ERROR` for unexpected errors

## Expected Benefits

After implementation:

1. **Simplified codebase** - 30-40% reduction in WebSocket/HTTP coordination code
2. **Eliminated race conditions** - No more timing-dependent bugs
3. **Better error messages** - Clear feedback when WebSocket connection missing
4. **More reliable gameplay** - Guaranteed real-time connection before game starts
5. **Easier debugging** - Single code path to follow and test
