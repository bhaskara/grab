"""
WebSocket event handlers for real-time game communication.

This module implements the WebSocket API specification for the Grab game server,
handling player connections, moves, and game state broadcasting.
"""

import json
import jwt
from flask import request, current_app
from flask_socketio import emit, join_room, leave_room, disconnect
from .api import game_server, active_sessions, verify_session_token
from .grab_state import DrawLetters


# Connected players: socket_id -> player_data
connected_players = {}

def get_connected_player_socket_id(username):
    """Find the socket ID for a connected player by username."""
    print(f"[DEBUG] Looking for socket ID for user {username}")
    print(f"[DEBUG] Connected players: {[(sid, data['username']) for sid, data in connected_players.items()]}")
    
    for socket_id, player_data in connected_players.items():
        if player_data['username'] == username:
            print(f"[DEBUG] Found socket ID {socket_id} for user {username}")
            return socket_id
    
    print(f"[DEBUG] No socket ID found for user {username}")
    return None

# Game rooms: game_id -> set of socket_ids
game_rooms = {}


def init_socketio_handlers(socketio):
    """Initialize WebSocket event handlers."""
    
    @socketio.on('connect')
    def handle_connect(auth):
        """Handle WebSocket connection with authentication."""
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
            
            # Store player connection info
            username = payload['username']
            connected_players[request.sid] = {
                'player_id': payload['player_id'],
                'username': username,
                'game_id': None  # Will be set if player is in an active game
            }
            
            # Check if player is in an active game and auto-join
            try:
                game_id = game_server.get_player_game(username)
                print(f"[DEBUG] Player {username} game lookup: {game_id}")
                if game_id:
                    # Check if game is active
                    game_data = game_server.get_game_metadata(game_id)
                    print(f"[DEBUG] Game {game_id} status: {game_data['status']}")
                    if game_data['status'] in ['waiting', 'active']:
                        # Join the game room
                        join_room(game_id)
                        connected_players[request.sid]['game_id'] = game_id
                        
                        # Add to game room tracking
                        if game_id not in game_rooms:
                            game_rooms[game_id] = set()
                        game_rooms[game_id].add(request.sid)
                        
                        print(f"[DEBUG] Player {username} joined room {game_id}, room now has {len(game_rooms[game_id])} members")
                        
                        # Send initial game state
                        game_state = _get_game_state(game_id)
                        emit('connected', {
                            'message': 'Successfully connected',
                            'game_state': game_state
                        })
                        
                        # Notify other players of reconnection
                        socketio.emit('player_reconnected', 
                                     {'player': username},
                                     room=game_id, 
                                     include_self=False)
                        return
            except KeyError:
                # Player doesn't exist in game server - continue with normal connection
                pass
            
            emit('connected', {'message': 'Successfully connected'})
            
        except Exception as e:
            emit('error', {'message': f'Connection error: {str(e)}'})
            return False
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle WebSocket disconnection."""
        if request.sid in connected_players:
            player_info = connected_players[request.sid]
            game_id = player_info.get('game_id')
            
            if game_id:
                # Notify other players in the game
                socketio.emit('player_disconnected', 
                             {'player': player_info['username']},
                             room=game_id)
                
                # Remove from game room
                if game_id in game_rooms:
                    game_rooms[game_id].discard(request.sid)
            
            # Remove from connected players
            del connected_players[request.sid]
    
    @socketio.on('move')
    def handle_move(data):
        """Handle player move attempts."""
        if request.sid not in connected_players:
            emit('move_result', {'success': False, 'error': 'Not authenticated'})
            return
        
        player_info = connected_players[request.sid]
        game_id = player_info.get('game_id')
        
        if not game_id:
            emit('move_result', {'success': False, 'error': 'Not in a game'})
            return
        
        move_data = data.get('data', '')
        username = player_info['username']
        
        print(f"[DEBUG] Player {username} making move '{move_data}' in game {game_id}")
        
        try:
            # Get the game object
            if game_id not in game_server.games:
                emit('move_result', {'success': False, 'error': 'Game not found'})
                return
            
            game_data = game_server.games[game_id]
            
            # Get the actual game object
            if 'game_object' in game_data:
                game = game_data['game_object']
            else:
                emit('move_result', {'success': False, 'error': 'Game not started'})
                return
            
            # Make the move - convert username to player index for Grab games
            if hasattr(game, 'handle_action'):
                # This is a Grab game - need to convert username to player index
                try:
                    state, players = game_server.get_game_info(game_id)
                    if username not in players:
                        emit('move_result', {'success': False, 'error': f'Player {username} not found in game'})
                        return
                    
                    player_index = players.index(username)
                    action = 0 if move_data == "" else move_data
                    
                    # Use handle_action for Grab games
                    new_state, move = game.handle_action(player_index, action)
                    
                    # Check if letters were drawn and emit special event
                    if isinstance(move, DrawLetters):
                        letters_remaining = int(sum(new_state.bag))
                        socketio.emit('letters_drawn', {
                            'data': {
                                'letters_drawn': move.letters,
                                'letters_remaining_in_bag': letters_remaining
                            }
                        }, room=game_id)
                        
                except Exception as e:
                    emit('move_result', {'success': False, 'error': str(e)})
                    return
            else:
                # This is a DummyGrab game - use send_move
                game.send_move(username, move_data)
            
            # Get updated game state
            game_state = _get_game_state(game_id)
            
            # Send success response to the player
            emit('move_result', {
                'success': True,
                'game_state': game_state
            })
            
            # Broadcast updated state to all players in the game
            print(f"[DEBUG] Broadcasting game_state to room {game_id}, room has {len(game_rooms.get(game_id, set()))} members")
            socketio.emit('game_state', {'data': game_state}, room=game_id)
            
        except ValueError as e:
            emit('move_result', {'success': False, 'error': str(e)})
        except Exception as e:
            emit('move_result', {'success': False, 'error': f'Move failed: {str(e)}'})
    
    @socketio.on('get_status')
    def handle_get_status():
        """Handle request for current game status."""
        if request.sid not in connected_players:
            emit('error', {'message': 'Not authenticated'})
            return
        
        player_info = connected_players[request.sid]
        game_id = player_info.get('game_id')
        
        if not game_id:
            emit('error', {'message': 'Not in a game'})
            return
        
        try:
            game_state = _get_game_state(game_id)
            emit('game_state', {'data': game_state})
        except Exception as e:
            emit('error', {'message': f'Failed to get game state: {str(e)}'})
    
    @socketio.on('player_action')
    def handle_player_action(data):
        """Handle player actions like ready_for_next_turn."""
        if request.sid not in connected_players:
            emit('error', {'message': 'Not authenticated'})
            return
        
        player_info = connected_players[request.sid]
        game_id = player_info.get('game_id')
        
        if not game_id:
            emit('error', {'message': 'Not in a game'})
            return
        
        action = data.get('data', '')
        username = player_info['username']
        
        if action == 'ready_for_next_turn':
            # For DummyGrab, this is equivalent to sending empty string
            try:
                if game_id not in game_server.games:
                    emit('error', {'message': 'Game not found'})
                    return
                
                game_data = game_server.games[game_id]
                
                # Get the actual game object
                if 'game_object' in game_data:
                    game = game_data['game_object']
                else:
                    emit('error', {'message': 'Game not started'})
                    return
                
                # Handle ready action - convert username to player index for Grab games
                if hasattr(game, 'handle_action'):
                    # This is a Grab game - need to convert username to player index
                    state, players = game_server.get_game_info(game_id)
                    if username not in players:
                        emit('error', {'message': f'Player {username} not found in game'})
                        return
                    
                    player_index = players.index(username)
                    # Use handle_action for Grab games (0 = pass)
                    new_state, move = game.handle_action(player_index, 0)
                    
                    # Check if letters were drawn and emit special event
                    if isinstance(move, DrawLetters):
                        letters_remaining = int(sum(new_state.bag))
                        socketio.emit('letters_drawn', {
                            'data': {
                                'letters_drawn': move.letters,
                                'letters_remaining_in_bag': letters_remaining
                            }
                        }, room=game_id)
                else:
                    # This is a DummyGrab game - use send_move
                    game.send_move(username, '')
                
                # Get updated game state
                game_state = _get_game_state(game_id)
                
                # Broadcast updated state to all players
                socketio.emit('game_state', {'data': game_state}, room=game_id)
                
            except Exception as e:
                emit('error', {'message': f'Action failed: {str(e)}'})
        else:
            emit('error', {'message': f'Unknown action: {action}'})
    
    @socketio.on('join_game_room')
    def handle_join_game_room(data):
        """Handle request to join a game room (triggered by REST API)."""
        print(f"[DEBUG] Received join_game_room event: {data}")
        
        if request.sid not in connected_players:
            emit('error', {'message': 'Not authenticated'})
            return
        
        player_info = connected_players[request.sid]
        game_id = data.get('game_id')
        username = player_info['username']
        
        print(f"[DEBUG] Player {username} attempting to join room {game_id}")
        
        if not game_id:
            emit('error', {'message': 'Game ID required'})
            return
        
        try:
            # Verify player is in this game
            if player_info['game_id'] != game_id:
                emit('error', {'message': 'Player not in this game'})
                return
            
            # Join the game room
            join_room(game_id)
            
            # Add to game room tracking
            if game_id not in game_rooms:
                game_rooms[game_id] = set()
            game_rooms[game_id].add(request.sid)
            
            print(f"[DEBUG] Player {username} successfully joined room {game_id}, room now has {len(game_rooms[game_id])} members")
            
            # Send current game state
            game_state = _get_game_state(game_id)
            emit('game_state', {'data': game_state})
            
        except Exception as e:
            emit('error', {'message': f'Failed to join game room: {str(e)}'})


def _get_game_state(game_id):
    """Get the current game state for a given game."""
    try:
        game_data = game_server.get_game_metadata(game_id)
    except KeyError:
        raise ValueError(f"Game {game_id} not found")
    
    # Get players and their connection status
    try:
        state, players = game_server.get_game_info(game_id)
        
        # Get game object for score calculation (only available after game is started)
        game_data = game_server.games[game_id]
        
        # Handle games that haven't been started yet
        if 'game_object' not in game_data:
            game_status = game_data.get('status', 'unknown')
            
            # Validate that this is indeed a game that hasn't started
            if game_status not in ['waiting']:
                raise ValueError(f"Game {game_id} has status '{game_status}' but no game_object. Expected 'waiting' status for games without game_object.")
            
            # Game not started yet - return basic waiting state
            players_dict = {}
            for username in players:
                is_connected = any(
                    player_data['username'] == username and player_data['game_id'] == game_id
                    for player_data in connected_players.values()
                )
                players_dict[username] = {
                    'connected': is_connected,
                    'score': 0,
                    'ready_for_next_turn': False
                }
            
            return {
                'game_id': game_id,
                'game_type': game_data.get('game_type', 'unknown'),
                'status': game_status,
                'current_turn': 0,
                'turn_time_remaining': None,
                'players': players_dict,
                'state': '{}'  # Empty state for waiting games
            }
        
        game = game_data['game_object']
        
        # Build players dict with connection info and actual scores
        players_dict = {}
        for username in players:
            is_connected = any(
                player_data['username'] == username and player_data['game_id'] == game_id
                for player_data in connected_players.values()
            )
            
            # Calculate actual score from game state
            actual_score = 0
            if hasattr(game, 'state'):
                player_index = players.index(username)
                actual_score = int(game.state.scores[player_index])
            
            players_dict[username] = {
                'connected': is_connected,
                'score': actual_score,
                'ready_for_next_turn': False  # TODO: Track from game state
            }
        
        # Get game-specific state
        if hasattr(game, 'get_state'):
            # DummyGrab - use get_state method
            is_running, current_round, history = game.get_state()
            game_state_json = json.dumps({
                'is_running': is_running,
                'current_round': current_round,
                'history': history,
                'current_moves': getattr(game, 'current_round_moves', {}),
                'players_done': list(getattr(game, 'players_done_current_round', set()))
            })
        elif hasattr(game, 'state'):
            # Grab game - use state attribute
            state = game.state
            game_state_json = json.dumps({
                'num_players': int(state.num_players),
                'pool': state.pool.tolist(),
                'bag': state.bag.tolist(),
                'words_per_player': [[word.word for word in words] for words in state.words_per_player],
                'scores': [int(score) for score in state.scores],
                'passed': [bool(passed) for passed in state.passed]
            })
        else:
            raise ValueError(f"Game object of type {type(game).__name__} has neither 'get_state' method nor 'state' attribute")
        
        return {
            'game_id': game_id,
            'game_type': game_data['game_type'],
            'status': game_data['status'],
            'current_turn': 1,  # TODO: Get from game state
            'turn_time_remaining': None,  # TODO: Implement time limits
            'players': players_dict,
            'state': game_state_json
        }
        
    except KeyError:
        raise ValueError(f"Game {game_id} not found in game server")