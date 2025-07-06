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
from src.grab.app import create_app
from src.grab.game_server import GameServer

@pytest.fixture
def app():
    """Create a test Flask application."""
    app, socketio = create_app({'TESTING': True})
    return app

@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    with patch('src.grab.api.game_server', GameServer()):
        with patch('src.grab.api.active_sessions', {}):
            with patch('src.grab.api.games_metadata', {}):
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
    
    def test_start_game_success(self, client, auth_headers):
        """Test successful game start."""
        # Create a game
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # Join the game
        client.post(f'/api/games/{game_id}/join', headers=auth_headers)
        
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
    
    def test_join_game_success(self, client, auth_headers):
        """Test successful game join."""
        # Create a game
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # Join the game
        response = client.post(f'/api/games/{game_id}/join', headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['game_id'] == game_id
        assert 'joined_at' in data['data']
    
    def test_join_game_not_found(self, client, auth_headers):
        """Test joining non-existent game."""
        response = client.post('/api/games/nonexistent/join', headers=auth_headers)
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Game not found' in data['error']
    
    def test_join_game_already_started(self, client, auth_headers, second_auth_headers):
        """Test joining game that's already started."""
        # Create and start a game
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # Join and start the game
        client.post(f'/api/games/{game_id}/join', headers=auth_headers)
        client.post(f'/api/games/{game_id}/start', headers=auth_headers)
        
        # Try to join as second user
        response = client.post(f'/api/games/{game_id}/join', headers=second_auth_headers)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Game has already started' in data['error']
    
    def test_join_game_twice(self, client, auth_headers):
        """Test joining same game twice."""
        # Create a game
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # Join the game
        response1 = client.post(f'/api/games/{game_id}/join', headers=auth_headers)
        assert response1.status_code == 200
        
        # Try to join again
        response2 = client.post(f'/api/games/{game_id}/join', headers=auth_headers)
        assert response2.status_code == 400
        data = json.loads(response2.data)
        assert data['success'] is False
        assert 'Player already in game' in data['error']
    
    def test_leave_game_success(self, client, auth_headers):
        """Test successful game leave."""
        # Create and join a game
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        game_id = json.loads(create_response.data)['data']['game_id']
        client.post(f'/api/games/{game_id}/join', headers=auth_headers)
        
        # Leave the game
        response = client.delete(f'/api/games/{game_id}/leave', headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['game_id'] == game_id
        assert 'left_at' in data['data']
    
    def test_leave_game_not_found(self, client, auth_headers):
        """Test leaving non-existent game."""
        response = client.delete('/api/games/nonexistent/leave', headers=auth_headers)
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Game not found' in data['error']
    
    def test_leave_game_not_in_game(self, client, auth_headers):
        """Test leaving game player is not in."""
        # Create a game but don't join
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # Try to leave without joining
        response = client.delete(f'/api/games/{game_id}/leave', headers=auth_headers)
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Player not in game' in data['error']

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
    
    def test_connect_websocket_game_not_active(self, client, auth_headers):
        """Test WebSocket connection to non-active game."""
        # Create and join a game but don't start it
        create_response = client.post('/api/games', 
                                     json={},
                                     headers=auth_headers,
                                     content_type='application/json')
        game_id = json.loads(create_response.data)['data']['game_id']
        client.post(f'/api/games/{game_id}/join', headers=auth_headers)
        
        # Try to connect without starting the game
        response = client.get(f'/api/games/{game_id}/connect', headers=auth_headers)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Game is not active' in data['error']

class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_complete_game_workflow(self, client, auth_headers, second_auth_headers):
        """Test complete game workflow from creation to start."""
        # Create a game
        create_response = client.post('/api/games', 
                                     json={'max_players': 2},
                                     headers=auth_headers,
                                     content_type='application/json')
        assert create_response.status_code == 201
        game_id = json.loads(create_response.data)['data']['game_id']
        
        # First player joins
        join_response1 = client.post(f'/api/games/{game_id}/join', headers=auth_headers)
        assert join_response1.status_code == 200
        
        # Second player joins
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
    
    def test_multiple_games_isolation(self, client, auth_headers, second_auth_headers):
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
        
        # Join different games
        client.post(f'/api/games/{game_id1}/join', headers=auth_headers)
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