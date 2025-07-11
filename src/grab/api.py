"""
HTTP API routes for the Grab game server.

This module implements the REST API endpoints for authentication,
game management, and player-game associations as specified in doc/server-api.md.
"""

import jwt
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Blueprint, request, jsonify, current_app
from .game_server import GameServer

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Global game server instance
game_server = GameServer()

# Active sessions: session_token -> player_data
active_sessions = {}


def create_session_token(player_id, username):
    """Create a JWT session token for a player."""
    payload = {
        'player_id': player_id,
        'username': username,
        'exp': datetime.now(timezone.utc) + timedelta(hours=24)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

def verify_session_token(token):
    """Verify and decode a JWT session token."""
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_auth(f):
    """Decorator to require authentication for API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        payload = verify_session_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired session token'}), 401
        
        request.current_user = payload
        return f(*args, **kwargs)
    return decorated_function

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """Authenticate a player with username only."""
    data = request.get_json()
    if not data or 'username' not in data:
        return jsonify({'success': False, 'error': 'Username is required'}), 400
    
    username = data['username'].strip()
    
    # Validate username format
    if not username or len(username) > 50 or not username.replace('_', '').isalnum():
        return jsonify({'success': False, 'error': 'Invalid username format'}), 400
    
    # Check if username is already taken by an active session
    for session_data in active_sessions.values():
        if session_data['username'] == username:
            return jsonify({'success': False, 'error': 'Username already taken'}), 409
    
    # Create new player session
    player_id = str(uuid.uuid4())
    session_token = create_session_token(player_id, username)
    
    # Store session data
    active_sessions[session_token] = {
        'player_id': player_id,
        'username': username,
        'created_at': datetime.now(timezone.utc).isoformat() + 'Z'
    }
    
    # Add player to game server
    try:
        game_server.add_player(username)
    except RuntimeError:
        # Player already exists in game server, that's fine
        pass
    
    return jsonify({
        'success': True,
        'data': {
            'player_id': player_id,
            'username': username,
            'session_token': session_token
        }
    }), 200

@api_bp.route('/games', methods=['POST'])
@require_auth
def create_game():
    """Create a new game."""
    data = request.get_json() or {}
    
    max_players = data.get('max_players', 4)
    time_limit_seconds = data.get('time_limit_seconds', 300)
    
    # Validate parameters
    if not isinstance(max_players, int) or max_players < 1 or max_players > 8:
        return jsonify({'success': False, 'error': 'Invalid max_players (must be 1-8)'}), 400
    
    if not isinstance(time_limit_seconds, int) or time_limit_seconds < 30:
        return jsonify({'success': False, 'error': 'Invalid time_limit_seconds (must be >= 30)'}), 400
    
    # Create game in game server with metadata
    game_id = game_server.add_game(
        creator_id=request.current_user['player_id'],
        creator_username=request.current_user['username'],
        max_players=max_players,
        time_limit_seconds=time_limit_seconds
    )
    
    game_data = game_server.get_game_metadata(game_id)
    return jsonify({
        'success': True,
        'data': {
            'game_id': game_id,
            'creator_id': game_data['creator_id'],
            'status': game_data['status'],
            'max_players': game_data['max_players'],
            'time_limit_seconds': game_data['time_limit_seconds'],
            'created_at': game_data['created_at']
        }
    }), 201

@api_bp.route('/games', methods=['GET'])
@require_auth
def get_all_games():
    """Get information about all games on the server."""
    games_list = []
    
    for game_id in game_server.list_games():
        try:
            game_data = game_server.get_game_metadata(game_id)
            # Get current players from game server
            try:
                state, players = game_server.get_game_info(game_id)
                current_players = []
                for username in players:
                    # Find player_id for this username
                    player_id = None
                    for session_data in active_sessions.values():
                        if session_data['username'] == username:
                            player_id = session_data['player_id']
                            break
                    
                    if player_id:
                        current_players.append({
                            'player_id': player_id,
                            'username': username,
                            'joined_at': game_data['created_at']  # Simplified for now
                        })
            except KeyError:
                current_players = []
            
            games_list.append({
                'game_id': game_id,
                'status': game_data['status'],
                'max_players': game_data['max_players'],
                'current_players': current_players,
                'creator_id': game_data['creator_id'],
                'created_at': game_data['created_at'],
                'started_at': game_data['started_at'],
                'finished_at': game_data['finished_at']
            })
        except KeyError:
            # Skip games that don't have metadata (shouldn't happen)
            continue
    
    return jsonify({
        'success': True,
        'data': {
            'games': games_list,
            'total_games': len(games_list)
        }
    }), 200

@api_bp.route('/games/<game_id>', methods=['GET'])
@require_auth
def get_game(game_id):
    """Get information about a specific game."""
    try:
        game_data = game_server.get_game_metadata(game_id)
    except KeyError:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    
    # Get current players from game server
    try:
        state, players = game_server.get_game_info(game_id)
        current_players = []
        for username in players:
            # Find player_id for this username
            player_id = None
            for session_data in active_sessions.values():
                if session_data['username'] == username:
                    player_id = session_data['player_id']
                    break
            
            if player_id:
                current_players.append({
                    'player_id': player_id,
                    'username': username,
                    'joined_at': game_data['created_at']  # Simplified for now
                })
    except KeyError:
        current_players = []
    
    return jsonify({
        'success': True,
        'data': {
            'game_id': game_id,
            'status': game_data['status'],
            'max_players': game_data['max_players'],
            'current_players': current_players,
            'creator_id': game_data['creator_id'],
            'created_at': game_data['created_at'],
            'started_at': game_data['started_at'],
            'finished_at': game_data['finished_at']
        }
    }), 200

@api_bp.route('/games/<game_id>/start', methods=['POST'])
@require_auth
def start_game(game_id):
    """Start a game that is waiting for players."""
    try:
        game_data = game_server.get_game_metadata(game_id)
    except KeyError:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    
    # Check if current user is the creator
    if game_data['creator_id'] != request.current_user['player_id']:
        return jsonify({'success': False, 'error': 'Only the game creator can start the game'}), 403
    
    # Check if game can be started
    if game_data['status'] != 'waiting':
        return jsonify({'success': False, 'error': 'Game cannot be started (wrong status)'}), 400
    
    # Get current players from game server
    try:
        state, players = game_server.get_game_info(game_id)
        if len(players) < 1:
            return jsonify({'success': False, 'error': 'Game cannot be started (not enough players)'}), 400
    except KeyError:
        return jsonify({'success': False, 'error': 'Game cannot be started (game not found)'}), 400
    
    # Start the game
    game_server.start_game(game_id)
    
    # Create game object based on game type
    game_type = current_app.config.get('GAME_TYPE', 'dummy')
    if game_type == 'dummy':
        from .dummy_grab import DummyGrab
        game_object = DummyGrab(list(players))
        # Store the game object in the game server, but keep the original structure
        original_game_data = game_server.games[game_id]
        game_server.games[game_id] = {
            'state': 'running',
            'players': original_game_data['players'],
            'game_object': game_object,
            # Keep all metadata
            'creator_id': original_game_data['creator_id'],
            'creator_username': original_game_data['creator_username'],
            'status': original_game_data['status'],
            'max_players': original_game_data['max_players'],
            'time_limit_seconds': original_game_data['time_limit_seconds'],
            'created_at': original_game_data['created_at'],
            'started_at': original_game_data['started_at'],
            'finished_at': original_game_data['finished_at']
        }
    else:
        return jsonify({'success': False, 'error': f'Unsupported game type: {game_type}'}), 400
    
    updated_game_data = game_server.get_game_metadata(game_id)
    return jsonify({
        'success': True,
        'data': {
            'game_id': game_id,
            'status': 'active',
            'started_at': updated_game_data['started_at']
        }
    }), 200

@api_bp.route('/games/<game_id>', methods=['DELETE'])
@require_auth
def stop_game(game_id):
    """Stop/cancel a game."""
    try:
        game_data = game_server.get_game_metadata(game_id)
    except KeyError:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    
    # Check if current user is the creator
    if game_data['creator_id'] != request.current_user['player_id']:
        return jsonify({'success': False, 'error': 'Only the game creator can stop the game'}), 403
    
    # Stop the game
    game_server.finish_game(game_id)
    
    # Update game server state
    try:
        game_server.set_game_state(game_id, 'done')
    except (KeyError, ValueError):
        pass  # Game server state management
    
    updated_game_data = game_server.get_game_metadata(game_id)
    return jsonify({
        'success': True,
        'data': {
            'game_id': game_id,
            'status': 'finished',
            'finished_at': updated_game_data['finished_at']
        }
    }), 200

@api_bp.route('/games/<game_id>/join', methods=['POST'])
@require_auth
def join_game(game_id):
    """Add the authenticated player to a game."""
    try:
        game_data = game_server.get_game_metadata(game_id)
    except KeyError:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    
    username = request.current_user['username']
    
    # Check if game has already started
    if game_data['status'] != 'waiting':
        return jsonify({'success': False, 'error': 'Game has already started'}), 400
    
    # Get current players from game server
    try:
        state, players = game_server.get_game_info(game_id)
        
        # Check if game is full
        if len(players) >= game_data['max_players']:
            return jsonify({'success': False, 'error': 'Game is full'}), 400
        
        # Check if player is already in this game
        if username in players:
            return jsonify({'success': False, 'error': 'Player already in game'}), 400
    except KeyError:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    
    # Check if player is in another active game by checking game server directly
    for other_game_id in game_server.list_games():
        if other_game_id != game_id:
            try:
                other_game_data = game_server.get_game_metadata(other_game_id)
                if other_game_data['status'] in ['waiting', 'active']:
                    try:
                        other_state, other_players = game_server.get_game_info(other_game_id)
                        if username in other_players:
                            return jsonify({'success': False, 'error': 'Player is already in another active game'}), 409
                    except KeyError:
                        pass
            except KeyError:
                pass
    
    # Add player to game server
    try:
        game_server.add_player_to_game(username, game_id)
    except KeyError:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    except RuntimeError as e:
        if "already in another game" in str(e):
            return jsonify({'success': False, 'error': 'Player is already in another active game'}), 409
        else:
            return jsonify({'success': False, 'error': str(e)}), 400
    
    joined_at = datetime.now(timezone.utc).isoformat() + 'Z'
    
    return jsonify({
        'success': True,
        'data': {
            'game_id': game_id,
            'player_id': request.current_user['player_id'],
            'joined_at': joined_at
        }
    }), 200


@api_bp.route('/games/<game_id>/connect')
@require_auth
def connect_websocket(game_id):
    """Establish WebSocket connection for real-time game communication."""
    try:
        game_data = game_server.get_game_metadata(game_id)
    except KeyError:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    
    username = request.current_user['username']
    
    # Check if player is in this game
    try:
        state, players = game_server.get_game_info(game_id)
        if username not in players:
            return jsonify({'success': False, 'error': 'Player not in this game'}), 403
    except KeyError:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    
    # Check if game is active
    if game_data['status'] != 'active':
        return jsonify({'success': False, 'error': 'Game is not active'}), 400
    
    # For WebSocket connections, the client should connect to Socket.IO endpoint
    # This endpoint validates the connection prerequisites
    return jsonify({
        'success': True,
        'data': {
            'message': 'Connection validated. Use Socket.IO to connect.',
            'game_id': game_id,
            'socketio_namespace': '/'
        }
    }), 200