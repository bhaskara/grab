"""
Tests for Flask application factory and basic functionality.
"""

import pytest
from src.grab.app import create_app

def test_create_app():
    """Test that the app factory creates a valid Flask app."""
    app, socketio = create_app()
    assert app is not None
    assert socketio is not None
    assert app.config['SECRET_KEY'] is not None