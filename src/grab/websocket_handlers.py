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


# Connected players: socket_id -> player_data
connected_players = {}

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
                if game_id:
                    # Check if game is active
                    game_data = game_server.get_game_metadata(game_id)
                    if game_data['status'] == 'active':
                        # Join the game room
                        join_room(game_id)
                        connected_players[request.sid]['game_id'] = game_id
                        
                        # Add to game room tracking
                        if game_id not in game_rooms:
                            game_rooms[game_id] = set()
                        game_rooms[game_id].add(request.sid)
                        
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
            
            # Make the move
            game.send_move(username, move_data)
            
            # Get updated game state
            game_state = _get_game_state(game_id)
            
            # Send success response to the player
            emit('move_result', {
                'success': True,
                'game_state': game_state
            })
            
            # Broadcast updated state to all players in the game
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
                
                game.send_move(username, '')
                
                # Get updated game state
                game_state = _get_game_state(game_id)
                
                # Broadcast updated state to all players
                socketio.emit('game_state', {'data': game_state}, room=game_id)
                
            except Exception as e:
                emit('error', {'message': f'Action failed: {str(e)}'})
        else:
            emit('error', {'message': f'Unknown action: {action}'})


def _get_game_state(game_id):
    """Get the current game state for a given game."""
    try:
        game_data = game_server.get_game_metadata(game_id)
    except KeyError:
        raise ValueError(f"Game {game_id} not found")
    
    # Get players and their connection status
    try:
        state, players = game_server.get_game_info(game_id)
        
        # Build players dict with connection info
        players_dict = {}
        for username in players:
            is_connected = any(
                player_data['username'] == username and player_data['game_id'] == game_id
                for player_data in connected_players.values()
            )
            
            players_dict[username] = {
                'connected': is_connected,
                'score': 0,  # TODO: Calculate from game state
                'ready_for_next_turn': False  # TODO: Track from game state
            }
        
        # Get game-specific state
        game_state_json = "{}"
        if game_id in game_server.games:
            game_data = game_server.games[game_id]
            if 'game_object' in game_data:
                game = game_data['game_object']
                if hasattr(game, 'get_state'):
                    is_running, current_round, history = game.get_state()
                    game_state_json = json.dumps({
                        'is_running': is_running,
                        'current_round': current_round,
                        'history': history,
                        'current_moves': getattr(game, 'current_round_moves', {}),
                        'players_done': list(getattr(game, 'players_done_current_round', set()))
                    })
        
        return {
            'game_id': game_id,
            'game_type': 'dummy',  # TODO: Get from game meta
            'status': game_data['status'],
            'current_turn': 1,  # TODO: Get from game state
            'turn_time_remaining': None,  # TODO: Implement time limits
            'players': players_dict,
            'state': game_state_json
        }
        
    except KeyError:
        raise ValueError(f"Game {game_id} not found in game server")