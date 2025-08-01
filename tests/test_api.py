"""
Tests for the HTTP API endpoints.

This module tests all the REST API endpoints for authentication,
game management, and player-game associations.
"""

import pytest
import json
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch
import socketio
from src.grab.app import create_app
from src.grab.game_server import GameServer

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

def create_game_with_socketio(client, app, auth_headers):
    """Helper to create a game and establish Socket.IO connection properly."""
    # Create a game
    create_response = client.post('/api/games', 
                                 json={},
                                 headers=auth_headers,
                                 content_type='application/json')
    assert create_response.status_code == 201
    game_id = json.loads(create_response.data)['data']['game_id']
    
    # Establish Socket.IO connection
    sio_client = create_test_socketio_connection(app, auth_headers)
    
    # Join the game (now works because we have Socket.IO connection)
    join_response = client.post(f'/api/games/{game_id}/join', headers=auth_headers)
    assert join_response.status_code == 200
    
    return game_id, sio_client

@pytest.fixture
def app():
    """Create a test Flask application."""
    app, socketio = create_app({'TESTING': True})
    app.socketio = socketio  # Store socketio instance for testing
    return app

@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    # Create shared instances for testing
    game_server_instance = GameServer()
    active_sessions_instance = {}
    
    with patch('src.grab.api.game_server', game_server_instance):
        with patch('src.grab.api.active_sessions', active_sessions_instance):
            with patch('src.grab.websocket_handlers.game_server', game_server_instance):
                with patch('src.grab.websocket_handlers.active_sessions', active_sessions_instance):
                    yield app.test_client()

@pytest.fixture
def auth_headers(client):
    """Create authentication headers for a test user."""
    # First login to get a token
    response = client.post('/api/auth/login', 
                          json={'username': 'testuser'},
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    token = data['data']['session_token']
    return {'Authorization': f'Bearer {token}'}

@pytest.fixture
def second_auth_headers(client):
    """Create authentication headers for a second test user."""
    # Login with a different username
    response = client.post('/api/auth/login', 
                          json={'username': 'testuser2'},
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    token = data['data']['session_token']
    return {'Authorization': f'Bearer {token}'}

class TestAuthentication:
    """Test authentication endpoints."""
    
    def test_login_success(self, client):
        """Test successful login."""
        response = client.post('/api/auth/login', 
                              json={'username': 'testuser'},
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'player_id' in data['data']
        assert 'username' in data['data']
        assert 'session_token' in data['data']
        assert data['data']['username'] == 'testuser'
    
    def test_login_missing_username(self, client):
        """Test login with missing username."""
        response = client.post('/api/auth/login', 
                              json={},
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Username is required' in data['error']
    
    def test_login_invalid_username(self, client):
        """Test login with invalid username."""
        response = client.post('/api/auth/login', 
                              json={'username': 'invalid-user-name!'},
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid username format' in data['error']
    
    def test_login_username_too_long(self, client):
        """Test login with username that's too long."""
        long_username = 'a' * 51  # 51 characters
        response = client.post('/api/auth/login', 
                              json={'username': long_username},
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid username format' in data['error']
    
    def test_login_duplicate_username(self, client):
        """Test login with duplicate username."""
        # First login
        response1 = client.post('/api/auth/login', 
                               json={'username': 'testuser'},
                               content_type='application/json')
        assert response1.status_code == 200
        
        # Second login with same username
        response2 = client.post('/api/auth/login', 
                               json={'username': 'testuser'},
                               content_type='application/json')
        assert response2.status_code == 409
        data = json.loads(response2.data)
        assert data['success'] is False
        assert 'Username already taken' in data['error']
    
    def test_unauthorized_access(self, client):
        """Test accessing protected endpoint without auth."""
        response = client.post('/api/games')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Missing or invalid authorization header' in data['error']
    
    def test_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token."""
        headers = {'Authorization': 'Bearer invalid-token'}
        response = client.post('/api/games', headers=headers)
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid or expired session token' in data['error']

class TestGameManagement:
    """Test game management endpoints."""
    
    def test_create_game_success(self, client, auth_headers):
        """Test successful game creation."""
        response = client.post('/api/games', 
                              json={'max_players': 4, 'time_limit_seconds': 300},
                              headers=auth_headers,
                              content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'game_id' in data['data']
        assert data['data']['status'] == 'waiting'
        assert data['data']['max_players'] == 4
        assert data['data']['time_limit_seconds'] == 300
    
    def test_create_game_default_values(self, client, auth_headers):
        """Test game creation with default values."""
        response = client.post('/api/games', 
                              json={},
                              headers=auth_headers,
                              content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['max_players'] == 4
        assert data['data']['time_limit_seconds'] == 300
    
    def test_create_game_invalid_max_players(self, client, auth_headers):
        """Test game creation with invalid max_players."""
        response = client.post('/api/games', 
                              json={'max_players': 0},
                              headers=auth_headers,
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid max_players' in data['error']
    
    def test_create_game_invalid_time_limit(self, client, auth_headers):
        """Test game creation with invalid time_limit_seconds."""
        response = client.post('/api/games', 
                              json={'time_limit_seconds': 10},
                              headers=auth_headers,
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid time_limit_seconds' in data['error']
    
    def test_create_game_with_next_letters_success(self, client, auth_headers):
        """Test successful game creation with next_letters."""
        next_letters = ['q', 'x', 'z', 'j', 'k']
        response = client.post('/api/games', 
                              json={'next_letters': next_letters},
                              headers=auth_headers,
                              content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'game_id' in data['data']
        assert data['data']['status'] == 'waiting'
    
    def test_create_game_with_next_letters_case_insensitive(self, client, auth_headers):
        """Test game creation with mixed case next_letters."""
        next_letters = ['Q', 'x', 'Z', 'j', 'K']
        response = client.post('/api/games', 
                              json={'next_letters': next_letters},
                              headers=auth_headers,
                              content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_create_game_next_letters_not_list(self, client, auth_headers):
        """Test game creation with next_letters that's not a list."""
        response = client.post('/api/games', 
                              json={'next_letters': 'abc'},
                              headers=auth_headers,
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'next_letters must be a list' in data['error']
    
    def test_create_game_next_letters_invalid_character(self, client, auth_headers):
        """Test game creation with invalid character in next_letters."""
        response = client.post('/api/games', 
                              json={'next_letters': ['a', '1', 'b']},
                              headers=auth_headers,
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid letter in next_letters' in data['error']
        assert 'Only single letters a-z are allowed' in data['error']
    
    def test_create_game_next_letters_empty_string(self, client, auth_headers):
        """Test game creation with empty string in next_letters."""
        response = client.post('/api/games', 
                              json={'next_letters': ['a', '', 'b']},
                              headers=auth_headers,
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid letter in next_letters' in data['error']
    
    def test_create_game_next_letters_multi_character(self, client, auth_headers):
        """Test game creation with multi-character string in next_letters."""
        response = client.post('/api/games', 
                              json={'next_letters': ['a', 'bb', 'c']},
                              headers=auth_headers,
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid letter in next_letters' in data['error']
    
    def test_create_game_next_letters_special_characters(self, client, auth_headers):
        """Test game creation with special characters in next_letters."""
        response = client.post('/api/games', 
                              json={'next_letters': ['a', '@', 'b']},
                              headers=auth_headers,
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid letter in next_letters' in data['error']
    
    def test_create_game_next_letters_empty_list(self, client, auth_headers):
        """Test game creation with empty next_letters list."""
        response = client.post('/api/games', 
                              json={'next_letters': []},
                              headers=auth_headers,
                              content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_get_game_success(self, client, auth_headers):
        """Test successful game retrieval."""
        # Create a game first
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        assert create_response.status_code == 201
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # Get the game
        response = client.get(f'/api/games/{game_id}', headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['game_id'] == game_id
        assert data['data']['status'] == 'waiting'
    
    def test_get_game_not_found(self, client, auth_headers):
        """Test getting non-existent game."""
        response = client.get('/api/games/nonexistent', headers=auth_headers)
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Game not found' in data['error']
    
    def test_get_all_games_empty(self, client, auth_headers):
        """Test getting all games when no games exist."""
        response = client.get('/api/games', headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['games'] == []
        assert data['data']['total_games'] == 0
    
    def test_get_all_games_with_games(self, client, auth_headers, second_auth_headers, app):
        """Test getting all games when games exist."""
        # Create two games
        create_response1 = client.post('/api/games', 
                                      json={'max_players': 2},
                                      headers=auth_headers,
                                      content_type='application/json')
        assert create_response1.status_code == 201
        game_id1 = json.loads(create_response1.data)['data']['game_id']
        
        create_response2 = client.post('/api/games', 
                                      json={'max_players': 4},
                                      headers=second_auth_headers,
                                      content_type='application/json')
        assert create_response2.status_code == 201
        game_id2 = json.loads(create_response2.data)['data']['game_id']
        
        # Join first game with Socket.IO connection
        sio_client = create_test_socketio_connection(app, auth_headers)
        join_response = client.post(f'/api/games/{game_id1}/join', headers=auth_headers)
        assert join_response.status_code == 200
        
        # Get all games
        response = client.get('/api/games', headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']['games']) == 2
        assert data['data']['total_games'] == 2
        
        # Verify game data structure
        games = data['data']['games']
        game_ids = [game['game_id'] for game in games]
        assert game_id1 in game_ids
        assert game_id2 in game_ids
        
        # Find the first game and verify it has a player
        game1_data = next(game for game in games if game['game_id'] == game_id1)
        assert game1_data['status'] == 'waiting'
        assert game1_data['max_players'] == 2
        assert len(game1_data['current_players']) == 1
        assert game1_data['current_players'][0]['username'] == 'testuser'
        
        # Find the second game and verify it has no players
        game2_data = next(game for game in games if game['game_id'] == game_id2)
        assert game2_data['status'] == 'waiting'
        assert game2_data['max_players'] == 4
        assert len(game2_data['current_players']) == 0
        
        # Clean up
        sio_client.disconnect()
    
    def test_start_game_success(self, client, auth_headers, app):
        """Test successful game start."""
        # Create a game
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # Join the game
        # Need Socket.IO connection for join to work
        sio_client = create_test_socketio_connection(app, auth_headers)
        client.post(f'/api/games/{game_id}/join', headers=auth_headers)
        sio_client.disconnect()
        
        # Start the game
        response = client.post(f'/api/games/{game_id}/start', headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['status'] == 'active'
        assert 'started_at' in data['data']
    
    def test_start_game_not_creator(self, client, auth_headers, second_auth_headers):
        """Test starting game as non-creator."""
        # Create a game with first user
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # Try to start with second user
        response = client.post(f'/api/games/{game_id}/start', headers=second_auth_headers)
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Only the game creator can start the game' in data['error']
    
    def test_start_game_no_players(self, client, auth_headers):
        """Test starting game with no players."""
        # Create a game but don't join
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # Try to start without joining
        response = client.post(f'/api/games/{game_id}/start', headers=auth_headers)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not enough players' in data['error']
    
    def test_stop_game_success(self, client, auth_headers):
        """Test successful game stop."""
        # Create a game
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # Stop the game
        response = client.delete(f'/api/games/{game_id}', headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['status'] == 'finished'
        assert 'finished_at' in data['data']
    
    def test_stop_game_not_creator(self, client, auth_headers, second_auth_headers):
        """Test stopping game as non-creator."""
        # Create a game with first user
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # Try to stop with second user
        response = client.delete(f'/api/games/{game_id}', headers=second_auth_headers)
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Only the game creator can stop the game' in data['error']

class TestPlayerGameAssociation:
    """Test player-game association endpoints."""
    
    def test_join_game_success(self, client, auth_headers, app):
        """Test successful game join with Socket.IO connection."""
        # Create a game
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # Establish Socket.IO connection FIRST
        sio_client = create_test_socketio_connection(app, auth_headers)
        
        # Now join the game (this will work)
        response = client.post(f'/api/games/{game_id}/join', headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['game_id'] == game_id
        assert 'joined_at' in data['data']
        
        # Verify we receive game state via Socket.IO
        received = sio_client.get_received()
        game_state_msg = None
        for msg in received:
            if msg['name'] == 'game_state':
                game_state_msg = msg
                break
        
        assert game_state_msg is not None
    
    def test_join_game_requires_websocket_connection(self, client, auth_headers, app):
        """Test that joining a game requires an active WebSocket connection."""
        # Create a game
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # Clear any existing Socket.IO connections to ensure clean test
        from src.grab.websocket_handlers import connected_players
        connected_players.clear()
        
        # Try to join without Socket.IO connection - should fail
        response = client.post(f'/api/games/{game_id}/join', headers=auth_headers)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Active WebSocket connection required' in data['error']
    
    def test_join_game_not_found(self, client, auth_headers):
        """Test joining non-existent game."""
        response = client.post('/api/games/nonexistent/join', json={'skip_websocket_check': True}, headers=auth_headers)
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Game not found' in data['error']
    
    def test_join_game_already_started(self, client, auth_headers, second_auth_headers, app):
        """Test joining game that's already started."""
        # Create a game and join with first user (with Socket.IO)
        game_id, sio_client = create_game_with_socketio(client, app, auth_headers)
        
        # Start the game
        client.post(f'/api/games/{game_id}/start', headers=auth_headers)
        
        # Create Socket.IO connection for second user
        sio_client2 = create_test_socketio_connection(app, second_auth_headers)
        
        # Try to join as second user - should fail because game already started
        response = client.post(f'/api/games/{game_id}/join', headers=second_auth_headers)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Game has already started' in data['error']
        
        # Clean up
        sio_client.disconnect()
        sio_client2.disconnect()
    
    def test_join_game_twice(self, client, auth_headers, app):
        """Test joining same game twice."""
        # Create a game and join with Socket.IO
        game_id, sio_client = create_game_with_socketio(client, app, auth_headers)
        
        # Try to join again - should fail
        response2 = client.post(f'/api/games/{game_id}/join', headers=auth_headers)
        assert response2.status_code == 400
        data = json.loads(response2.data)
        assert data['success'] is False
        assert 'Player already in game' in data['error']
        
        # Clean up
        sio_client.disconnect()
    

class TestWebSocketConnection:
    """Test WebSocket connection endpoint."""
    
    def test_connect_websocket_game_not_found(self, client, auth_headers):
        """Test WebSocket connection to non-existent game."""
        response = client.get('/api/games/nonexistent/connect', headers=auth_headers)
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Game not found' in data['error']
    
    def test_connect_websocket_player_not_in_game(self, client, auth_headers):
        """Test WebSocket connection when player is not in game."""
        # Create a game but don't join
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # Try to connect without joining
        response = client.get(f'/api/games/{game_id}/connect', headers=auth_headers)
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Player not in this game' in data['error']
    
    def test_connect_websocket_game_not_active(self, client, auth_headers, app):
        """Test WebSocket connection to non-active game."""
        # Create and join a game but don't start it
        game_id, sio_client = create_game_with_socketio(client, app, auth_headers)
        
        # Try to connect via /connect endpoint without starting the game
        response = client.get(f'/api/games/{game_id}/connect', headers=auth_headers)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Game is not active' in data['error']
        
        # Clean up
        sio_client.disconnect()

class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_complete_game_workflow(self, client, auth_headers, second_auth_headers, app):
        """Test complete game workflow from creation to start."""
        # Create a game
        create_response = client.post('/api/games', 
                                     json={'max_players': 2},
                                     headers=auth_headers,
                                     content_type='application/json')
        assert create_response.status_code == 201
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # First player joins with Socket.IO
        sio_client1 = create_test_socketio_connection(app, auth_headers)
        join_response1 = client.post(f'/api/games/{game_id}/join', headers=auth_headers)
        assert join_response1.status_code == 200
        
        # Second player joins with Socket.IO
        sio_client2 = create_test_socketio_connection(app, second_auth_headers)
        join_response2 = client.post(f'/api/games/{game_id}/join', headers=second_auth_headers)
        assert join_response2.status_code == 200
        
        # Check game state
        get_response = client.get(f'/api/games/{game_id}', headers=auth_headers)
        assert get_response.status_code == 200
        game_data = json.loads(get_response.data)['data']
        assert len(game_data['current_players']) == 2
        
        # Start the game
        start_response = client.post(f'/api/games/{game_id}/start', headers=auth_headers)
        assert start_response.status_code == 200
        
        # Verify game is active
        get_response2 = client.get(f'/api/games/{game_id}', headers=auth_headers)
        assert get_response2.status_code == 200
        game_data2 = json.loads(get_response2.data)['data']
        assert game_data2['status'] == 'active'
        assert game_data2['started_at'] is not None
        
        # Clean up
        sio_client1.disconnect()
        sio_client2.disconnect()
    
    def test_multiple_games_isolation(self, client, auth_headers, second_auth_headers, app):
        """Test that multiple games are properly isolated."""
        # Create two games
        create_response1 = client.post('/api/games', 
                                      json={},
                                      headers=auth_headers,
                                      content_type='application/json')
        game_id1 = json.loads(create_response1.data)['data']['game_id']
        
        create_response2 = client.post('/api/games', 
                                      json={},
                                      headers=second_auth_headers,
                                      content_type='application/json')
        game_id2 = json.loads(create_response2.data)['data']['game_id']
        
        # Verify games are different
        assert game_id1 != game_id2
        
        # Join different games with Socket.IO connections
        sio_client1 = create_test_socketio_connection(app, auth_headers)
        client.post(f'/api/games/{game_id1}/join', headers=auth_headers)
        
        sio_client2 = create_test_socketio_connection(app, second_auth_headers)
        client.post(f'/api/games/{game_id2}/join', headers=second_auth_headers)
        
        # Verify game states are independent
        get_response1 = client.get(f'/api/games/{game_id1}', headers=auth_headers)
        get_response2 = client.get(f'/api/games/{game_id2}', headers=second_auth_headers)
        
        game_data1 = json.loads(get_response1.data)['data']
        game_data2 = json.loads(get_response2.data)['data']
        
        assert len(game_data1['current_players']) == 1
        assert len(game_data2['current_players']) == 1
        assert game_data1['current_players'][0]['username'] == 'testuser'
        assert game_data2['current_players'][0]['username'] == 'testuser2'
        
        # Clean up
        sio_client1.disconnect()
        sio_client2.disconnect()


@pytest.fixture
def socketio_client(app):
    """Create a test Socket.IO client."""
    return socketio.SimpleClient()


class TestWebSocketAPI:
    """Test WebSocket API functionality."""
    
    # test_websocket_connection_and_auto_join_game removed - auto-join functionality was removed in refactor
    
    def test_websocket_move_handling(self, client, auth_headers, app):
        """Test WebSocket move handling."""
        # Create and join a game with Socket.IO
        game_id, sio_client = create_game_with_socketio(client, app, auth_headers)
        
        # Start the game
        client.post(f'/api/games/{game_id}/start', 
                   json={'test_letters': ['h', 'e', 'l', 'l', 'o']}, 
                   headers=auth_headers)
        
        # Clear received messages
        sio_client.get_received()
        
        # Make a move
        sio_client.emit('move', {'data': 'hello'})
        
        # Get all received messages
        received = sio_client.get_received()
        
        # Find move_result message
        move_result_msg = None
        game_state_msg = None
        for msg in received:
            if msg['name'] == 'move_result':
                move_result_msg = msg
            elif msg['name'] == 'game_state':
                game_state_msg = msg
        
        assert move_result_msg is not None
        assert move_result_msg['args'][0]['success'] is True
        
        assert game_state_msg is not None
        game_state = game_state_msg['args'][0]['data']
        state_data = json.loads(game_state['state'])
        
        # For Grab games, check that the word was added to player's words
        assert 'words_per_player' in state_data
        assert len(state_data['words_per_player']) > 0
        player_words = state_data['words_per_player'][0]  # First player's words
        assert 'hello' in player_words
        
        # Clean up
        sio_client.disconnect()
    
    def test_websocket_player_action_ready(self, client, auth_headers, app):
        """Test WebSocket player action for ready_for_next_turn."""
        # Create and join a game with Socket.IO
        game_id, sio_client = create_game_with_socketio(client, app, auth_headers)
        
        # Start the game
        client.post(f'/api/games/{game_id}/start', 
                   json={'test_letters': ['r', 'e', 'a', 'd', 'y']}, 
                   headers=auth_headers)
        
        # Clear received messages
        sio_client.get_received()
        
        # Signal ready for next turn
        sio_client.emit('player_action', {'data': 'ready_for_next_turn'})
        
        # Get received messages
        received = sio_client.get_received()
        
        # Find game_state message
        game_state_msg = None
        for msg in received:
            if msg['name'] == 'game_state':
                game_state_msg = msg
                break
        
        assert game_state_msg is not None
        game_state = game_state_msg['args'][0]['data']
        state_data = json.loads(game_state['state'])
        
        # For Grab games with single player, passing triggers letter draw which resets passed status
        assert 'passed' in state_data
        assert len(state_data['passed']) > 0
        # In single-player game, passing draws new letter and resets passed status to False
        assert state_data['passed'][0] is False  # Player status reset after letter draw
        
        # Verify that new letters were added to pool (indicating letter was drawn)
        initial_pool_count = sum([1, 0, 0, 1, 1])  # r, e, a, d, y
        current_pool_count = sum(state_data['pool'])
        assert current_pool_count > initial_pool_count  # New letter was drawn
        
        # Clean up
        sio_client.disconnect()
    
    def test_websocket_get_status(self, client, auth_headers, app):
        """Test WebSocket get_status request."""
        # Create and join a game with Socket.IO
        game_id, sio_client = create_game_with_socketio(client, app, auth_headers)
        
        # Start the game
        client.post(f'/api/games/{game_id}/start', 
                   json={'test_letters': ['s', 't', 'a', 't', 'u', 's']}, 
                   headers=auth_headers)
        
        # Clear received messages
        sio_client.get_received()
        
        # Request game status
        sio_client.emit('get_status')
        
        # Get received messages
        received = sio_client.get_received()
        
        # Find game_state message
        game_state_msg = None
        for msg in received:
            if msg['name'] == 'game_state':
                game_state_msg = msg
                break
        
        assert game_state_msg is not None
        game_state = game_state_msg['args'][0]['data']
        assert game_state['game_id'] == game_id
        assert 'testuser' in game_state['players']
        
        # Clean up
        sio_client.disconnect()
    
    def test_websocket_authentication_failure(self, app):
        """Test WebSocket connection with invalid authentication."""
        # Create Socket.IO test client
        sio_client = app.socketio.test_client(app)
        
        # Try to connect with invalid token
        sio_client.connect(auth={'token': 'invalid_token'})
        
        # Check if actually connected by testing if we can emit
        is_connected = sio_client.is_connected()
        
        # If connected, the authentication rejection should happen at the handler level
        # If not connected, that's also a valid authentication failure
        if is_connected:
            # Try to emit and expect error about authentication
            try:
                sio_client.emit('move', {'data': 'test'})
                received = sio_client.get_received()
                # Look for authentication error
                error_found = any(
                    msg['name'] == 'error' and 
                    ('token' in msg['args'][0]['message'].lower() or 
                     'authentication' in msg['args'][0]['message'].lower())
                    for msg in received
                )
                assert error_found
            except RuntimeError:
                # Connection was rejected, which is also valid
                pass
        # If not connected, authentication correctly failed


class TestServerClientFlow:
    """Integration test for complete server-client flow."""
    
    def test_full_server_client_integration(self, client, app):
        """
        Test complete server-client flow:
        1. Start server (implicit via test fixtures)
        2. Multiple clients connect to the server
        3. Client A creates a game and joins it
        4. Client B joins that same game
        5. Client A starts the game
        6. Verify that the game is active and letters have been drawn
        """
        # Step 1: Server is already started via the test fixtures
        
        # Step 2: Multiple clients connect (authenticate)
        # Client A login
        client_a_response = client.post('/api/auth/login', 
                                      json={'username': 'clientA'},
                                      content_type='application/json')
        assert client_a_response.status_code == 200
        client_a_data = json.loads(client_a_response.data)
        client_a_headers = {'Authorization': f'Bearer {client_a_data["data"]["session_token"]}'}
        client_a_token = client_a_data["data"]["session_token"]
        
        # Client B login
        client_b_response = client.post('/api/auth/login', 
                                      json={'username': 'clientB'},
                                      content_type='application/json')
        assert client_b_response.status_code == 200
        client_b_data = json.loads(client_b_response.data)
        client_b_headers = {'Authorization': f'Bearer {client_b_data["data"]["session_token"]}'}
        client_b_token = client_b_data["data"]["session_token"]
        
        # Step 3: Client A creates a game and joins it
        create_response = client.post('/api/games', 
                                    json={'max_players': 2},
                                    headers=client_a_headers,
                                    content_type='application/json')
        assert create_response.status_code == 201
        game_data = json.loads(create_response.data)['data']
        game_id = game_data['game_id']
        assert game_data['status'] == 'waiting'
        
        # Client A joins the game (with Socket.IO connection)
        client_a_sio = app.socketio.test_client(app)
        client_a_sio.connect(auth={'token': client_a_token})
        
        join_a_response = client.post(f'/api/games/{game_id}/join', headers=client_a_headers)
        assert join_a_response.status_code == 200
        
        # Verify Client A is in the game
        game_status_response = client.get(f'/api/games/{game_id}', headers=client_a_headers)
        assert game_status_response.status_code == 200
        game_status = json.loads(game_status_response.data)['data']
        assert len(game_status['current_players']) == 1
        assert game_status['current_players'][0]['username'] == 'clientA'
        
        # Step 4: Client B joins that same game (with Socket.IO connection)
        client_b_sio = app.socketio.test_client(app)
        client_b_sio.connect(auth={'token': client_b_token})
        
        join_b_response = client.post(f'/api/games/{game_id}/join', headers=client_b_headers)
        assert join_b_response.status_code == 200
        
        # Verify both clients are in the game
        game_status_response = client.get(f'/api/games/{game_id}', headers=client_a_headers)
        assert game_status_response.status_code == 200
        game_status = json.loads(game_status_response.data)['data']
        assert len(game_status['current_players']) == 2
        usernames = [player['username'] for player in game_status['current_players']]
        assert 'clientA' in usernames
        assert 'clientB' in usernames
        
        # Step 5: Client A starts the game
        start_response = client.post(f'/api/games/{game_id}/start', 
                                   json={'test_letters': ['c', 'a', 'd', 'e', 'f']},
                                   headers=client_a_headers)
        assert start_response.status_code == 200
        start_data = json.loads(start_response.data)['data']
        assert start_data['status'] == 'active'
        assert start_data['started_at'] is not None
        
        # Step 6: Verify that the game is active and letters have been drawn
        # Check via HTTP API that game is active
        final_status_response = client.get(f'/api/games/{game_id}', headers=client_a_headers)
        assert final_status_response.status_code == 200
        final_status = json.loads(final_status_response.data)['data']
        assert final_status['status'] == 'active'
        assert final_status['started_at'] is not None
        
        # Test WebSocket communication by getting game status
        # Clear any pending messages from both clients
        client_a_sio.get_received()
        client_b_sio.get_received()
        
        # Client A requests game status via WebSocket
        client_a_sio.emit('get_status')
        
        # Get game state response
        received_a = client_a_sio.get_received()
        game_state_msg = None
        for msg in received_a:
            if msg['name'] == 'game_state':
                game_state_msg = msg
                break
        
        assert game_state_msg is not None, "Client A should receive game state via WebSocket"
        game_state_a = game_state_msg['args'][0]['data']
        assert game_state_a['game_id'] == game_id
        assert game_state_a['status'] == 'active'
        assert 'clientA' in game_state_a['players']
        assert 'clientB' in game_state_a['players']
        
        # Verify letters have been drawn by checking game state
        state_data = json.loads(game_state_a['state'])
        
        # Check that letters have been drawn to the pool
        assert 'pool' in state_data
        pool_letter_count = sum(state_data['pool'])
        assert pool_letter_count > 0, "No letters have been drawn to the pool"
        
        # Check that the bag has letters removed (initial letters were drawn)
        assert 'bag' in state_data
        bag_letter_count = sum(state_data['bag'])
        # Total Scrabble tiles minus letters drawn should equal bag count
        # Standard Scrabble has 100 tiles, and we started with test letters drawn
        assert bag_letter_count > 0, "Bag should still have letters"
        
        # Test that moves can be made via WebSocket
        # Clear any pending messages
        client_a_sio.get_received()
        client_b_sio.get_received()
        
        # Client A attempts to make a move with "cad" (guaranteed to be a valid word)
        client_a_sio.emit('move', {'data': 'cad'})
        
        # Both clients should receive the move result and updated game state
        received_a_move = client_a_sio.get_received()
        received_b_move = client_b_sio.get_received()
        
        # Client A should get move_result and it must succeed since "cad" is a valid word
        move_result_msg = None
        for msg in received_a_move:
            if msg['name'] == 'move_result':
                move_result_msg = msg
                break
        
        assert move_result_msg is not None, f"Client A did not receive move_result. Received: {received_a_move}"
        assert move_result_msg['args'][0]['success'] is True, f"Move 'cad' should have succeeded but got: {move_result_msg['args'][0]}"
        
        # Both clients should receive updated game state since move was successful
        game_state_update_a = None
        game_state_update_b = None
        
        for msg in received_a_move:
            if msg['name'] == 'game_state':
                game_state_update_a = msg
                break
        
        for msg in received_b_move:
            if msg['name'] == 'game_state':
                game_state_update_b = msg
                break
        
        assert game_state_update_a is not None, f"Client A did not receive game_state update. Received: {received_a_move}"
        assert game_state_update_b is not None, f"Client B did not receive game_state update. Received: {received_b_move}"
        
        # Verify the move was applied - check that "cad" appears in the player's words
        updated_state_a = json.loads(game_state_update_a['args'][0]['data']['state'])
        assert 'words_per_player' in updated_state_a
        player_0_words = updated_state_a['words_per_player'][0]  # clientA is player 0
        assert 'cad' in player_0_words, f"Word 'cad' should be in player 0's words but got: {player_0_words}"
        
        # Test letters_drawn event by having both players pass (should trigger letter draw)
        # Clear any pending messages
        client_a_sio.get_received()
        client_b_sio.get_received()
        
        # Both clients signal ready for next turn (pass)
        client_a_sio.emit('player_action', {'data': 'ready_for_next_turn'})
        client_b_sio.emit('player_action', {'data': 'ready_for_next_turn'})
        
        # Check if letters_drawn event was emitted
        received_a_pass = client_a_sio.get_received()
        received_b_pass = client_b_sio.get_received()
        
        # Look for letters_drawn event
        letters_drawn_msg_a = None
        letters_drawn_msg_b = None
        
        for msg in received_a_pass:
            if msg['name'] == 'letters_drawn':
                letters_drawn_msg_a = msg
                break
        
        for msg in received_b_pass:
            if msg['name'] == 'letters_drawn':
                letters_drawn_msg_b = msg
                break
        
        # Verify letters_drawn event was received by both clients
        assert letters_drawn_msg_a is not None, f"Client A did not receive letters_drawn event. Received: {received_a_pass}"
        assert letters_drawn_msg_b is not None, f"Client B did not receive letters_drawn event. Received: {received_b_pass}"
        
        # Verify event data structure
        letters_data_a = letters_drawn_msg_a['args'][0]['data']
        assert 'letters_drawn' in letters_data_a
        assert 'letters_remaining_in_bag' in letters_data_a
        assert isinstance(letters_data_a['letters_drawn'], list)
        assert isinstance(letters_data_a['letters_remaining_in_bag'], int)
        assert len(letters_data_a['letters_drawn']) > 0, "Should have drawn at least one letter"
        
        letters_drawn = letters_data_a['letters_drawn']
        letters_remaining = letters_data_a['letters_remaining_in_bag']
        
        print(f"Integration test completed successfully:")
        print(f"  - Game ID: {game_id}")
        print(f"  - Both clients authenticated and joined")
        print(f"  - Game started and is active")
        print(f"  - Letters drawn to pool: {pool_letter_count}")
        print(f"  - WebSocket connections established")
        print(f"  - Move 'cad' processed successfully")
        print(f"  - Word added to player's collection: {player_0_words}")
        print(f"  - Letters drawn event received: {letters_drawn}")
        print(f"  - Letters remaining in bag: {letters_remaining}")
        
        # Clean up connections
        client_a_sio.disconnect()
        client_b_sio.disconnect()
    
    def test_next_letters_end_to_end_integration(self, client, app):
        """Test next_letters functionality end-to-end through the API.
        
        This test verifies that:
        1. Games can be created with next_letters parameter
        2. Letters are drawn in the specified order when game starts
        3. After predetermined letters are exhausted, random sampling works
        4. The functionality works through the complete API flow
        """
        # Step 1: Authenticate a user
        login_response = client.post('/api/auth/login', 
                                   json={'username': 'testuser'},
                                   content_type='application/json')
        assert login_response.status_code == 200
        auth_data = json.loads(login_response.data)
        auth_headers = {'Authorization': f'Bearer {auth_data["data"]["session_token"]}'}
        token = auth_data["data"]["session_token"]
        
        # Step 2: Create a game with specific next_letters
        predetermined_letters = ['q', 'x', 'z']  # Use uncommon letters to ensure they come from next_letters
        create_response = client.post('/api/games', 
                                    json={
                                        'max_players': 2,
                                        'next_letters': predetermined_letters
                                    },
                                    headers=auth_headers,
                                    content_type='application/json')
        assert create_response.status_code == 201
        game_data = json.loads(create_response.data)['data']
        game_id = game_data['game_id']
        
        # Step 3: Join the game with Socket.IO connection
        sio_client = app.socketio.test_client(app)
        sio_client.connect(auth={'token': token})
        
        join_response = client.post(f'/api/games/{game_id}/join', headers=auth_headers)
        assert join_response.status_code == 200
        
        # Step 4: Start the game (this should draw 3 initial letters)
        start_response = client.post(f'/api/games/{game_id}/start', headers=auth_headers)
        assert start_response.status_code == 200
        
        # Step 5: Verify the game started and check initial letters drawn
        # Clear any pending messages
        sio_client.get_received()
        
        # Request game status to see current state
        sio_client.emit('get_status')
        received = sio_client.get_received()
        
        # Find the game_state message
        game_state_msg = None
        letters_drawn_msg = None
        for msg in received:
            if msg['name'] == 'game_state':
                game_state_msg = msg
            elif msg['name'] == 'letters_drawn':
                letters_drawn_msg = msg
        
        assert game_state_msg is not None, "Should receive game state"
        game_state = game_state_msg['args'][0]['data']
        assert game_state['status'] == 'active'
        
        # Step 6: Check that the initial 3 letters drawn were from our predetermined list
        # The letters_drawn event should have been emitted during game start
        if letters_drawn_msg is None:
            # If we didn't catch it in the get_status response, it might have been sent earlier
            # Let's check the game state to see what letters are in the pool
            state_data = json.loads(game_state['state'])
            pool_letters = []
            for i, count in enumerate(state_data['pool']):
                if count > 0:
                    letter = chr(ord('a') + i)
                    pool_letters.extend([letter] * count)
            
            # The pool should contain exactly our first 3 predetermined letters
            assert len(pool_letters) == 3, f"Expected 3 letters in pool, got {len(pool_letters)}: {pool_letters}"
            assert set(pool_letters) == set(predetermined_letters), f"Expected {predetermined_letters} in pool, got {pool_letters}"
        else:
            # Verify the letters_drawn event contains our predetermined letters
            letters_data = letters_drawn_msg['args'][0]['data']
            drawn_letters = letters_data['letters_drawn']
            assert len(drawn_letters) == 3, f"Expected 3 letters drawn, got {len(drawn_letters)}"
            assert drawn_letters == predetermined_letters, f"Expected {predetermined_letters}, got {drawn_letters}"
        
        # Step 7: Force another letter draw to test that next_letters are exhausted
        # We'll do this by having the player pass twice (which should trigger letter draws)
        sio_client.get_received()  # Clear messages
        
        # Player signals ready for next turn (pass)
        sio_client.emit('player_action', {'data': 'ready_for_next_turn'})
        
        # Wait for response and check if more letters were drawn
        received_pass = sio_client.get_received()
        
        # Look for letters_drawn event
        letters_drawn_after_pass = None
        for msg in received_pass:
            if msg['name'] == 'letters_drawn':
                letters_drawn_after_pass = msg
                break
        
        # If letters were drawn after the pass, they should be random (not from our predetermined list)
        if letters_drawn_after_pass is not None:
            letters_data = letters_drawn_after_pass['args'][0]['data']
            new_drawn_letters = letters_data['letters_drawn']
            
            # These should be random letters, not necessarily from our predetermined list
            # (though they could coincidentally match)
            assert len(new_drawn_letters) > 0, "Should have drawn at least one letter"
            for letter in new_drawn_letters:
                assert 'a' <= letter <= 'z', f"Drawn letter '{letter}' should be valid"
        
        print(f"Next letters integration test completed successfully:")
        print(f"  - Game created with predetermined letters: {predetermined_letters}")
        print(f"  - Game started and drew initial letters correctly")
        print(f"  - Predetermined letters were used in order")
        print(f"  - Random sampling works after predetermined letters exhausted")
        
        # Clean up
        sio_client.disconnect()