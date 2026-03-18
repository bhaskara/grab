"""
WebSocket event handlers for real-time game communication.

This module implements the WebSocket API specification for the Grab game server,
handling player connections, moves, and game state broadcasting.
"""

import json
import jwt
import numpy as np
from flask import request, current_app
from flask_socketio import emit, join_room, leave_room, disconnect
from loguru import logger
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

            # Guard: reject moves on finished games
            if game_data.get('status') == 'finished':
                emit('move_result', {'success': False, 'error': 'Game has ended'})
                return

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
                    
                    # Check if the game ended naturally
                    if _check_and_handle_game_end(game_id, new_state, move, socketio):
                        emit('move_result', {'success': True, 'game_state': _get_game_state(game_id)})
                        return

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

                # Guard: reject actions on finished games
                if game_data.get('status') == 'finished':
                    emit('error', {'message': 'Game has ended'})
                    return

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

                    # Check if the game ended naturally
                    if _check_and_handle_game_end(game_id, new_state, move, socketio):
                        return

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

    @socketio.on('confirm_game_end')
    def handle_confirm_game_end():
        """Handle the creator confirming the game-over transition.

        When the bag is empty and all players have passed, the game enters a
        pending state where only the creator can trigger the game-over screen
        for all players. This handler validates that the requesting player is
        the authenticated game creator, then broadcasts a ``show_game_over``
        event to every player in the game room so they all transition to the
        game-over screen simultaneously.
        """
        if request.sid not in connected_players:
            emit('error', {'message': 'Not authenticated'})
            return

        player_info = connected_players[request.sid]
        game_id = player_info.get('game_id')
        username = player_info['username']

        if not game_id:
            emit('error', {'message': 'Not in a game'})
            return

        if game_id not in game_server.games:
            emit('error', {'message': 'Game not found'})
            return

        game_data = game_server.games[game_id]

        # Only allow on finished games
        if game_data.get('status') != 'finished':
            emit('error', {'message': 'Game is not finished'})
            return

        # Only the creator may confirm the game end
        if game_data.get('creator_username') != username:
            emit('error', {'message': 'Only the game creator can confirm game end'})
            return

        # Build game-over payload from current state
        _, players = game_server.get_game_info(game_id)
        game = game_data.get('game_object')
        if game and hasattr(game, 'state'):
            final_scores = {
                players[i]: int(game.state.scores[i])
                for i in range(len(players))
            }
        else:
            final_scores = {p: 0 for p in players}
        winner = max(final_scores, key=final_scores.get) if final_scores else None

        socketio.emit('show_game_over', {
            'final_scores': final_scores,
            'winner': winner,
            'reason': 'bag_empty',
        }, room=game_id)

        logger.info(f"Game {game_id}: creator '{username}' confirmed game end, broadcast show_game_over")


def _check_and_handle_game_end(game_id, new_state, move, socketio):
    """Check if the game has naturally ended and handle the transition.

    A natural game end occurs when the bag is empty, all players have passed,
    and no move was made (move is None). When detected, this function transitions
    the game to 'finished' status, emits the ``game_ending`` event with final
    scores, and broadcasts the final game state.

    Parameters
    ----------
    game_id : str
        The ID of the game to check.
    new_state : State
        The game state after the most recent action.
    move : Move or None
        The move that resulted from the action. ``None`` when all players
        passed and the bag was already empty (i.e. ``end_game`` was called).
    socketio : SocketIO
        The Socket.IO server instance used to emit events.

    Returns
    -------
    bool
        ``True`` if the game ended and callers should stop further processing,
        ``False`` otherwise.
    """
    if move is not None:
        return False
    if np.sum(new_state.bag) > 0:
        return False
    if not all(new_state.passed):
        return False

    # Game has naturally ended — transition state
    game_server.finish_game(game_id)
    game_server.set_game_state(game_id, 'done')

    # Build final scores and determine winner
    game_data = game_server.games[game_id]
    _, players = game_server.get_game_info(game_id)
    final_scores = {
        players[i]: int(new_state.scores[i])
        for i in range(len(players))
    }
    winner = max(final_scores, key=final_scores.get)

    # Get final game state for the event payload
    final_game_state = _get_game_state(game_id)

    socketio.emit('game_ending', {
        'reason': 'bag_empty',
        'final_scores': final_scores,
        'winner': winner,
        'final_game_state': final_game_state,
    }, room=game_id)

    socketio.emit('game_state', {'data': final_game_state}, room=game_id)

    logger.info(f"Game {game_id} ended naturally (bag empty, all passed). Winner: {winner}")
    return True


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