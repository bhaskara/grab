"""
Flask application factory and main application entry point.

This module creates and configures the Flask application instance
with WebSocket support for real-time game communication.
"""

from flask import Flask
from flask_socketio import SocketIO

def create_app(config=None):
    """
    Create and configure the Flask application.
    
    Args:
        config: Configuration object or dictionary
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Default configuration
    app.config.update({
        'SECRET_KEY': 'dev-key-change-in-production',
        'DEBUG': True
    })
    
    if config:
        app.config.update(config)
    
    # Initialize SocketIO for WebSocket support
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Register blueprints/routes here
    from . import routes
    app.register_blueprint(routes.bp)
    
    from . import api
    app.register_blueprint(api.api_bp)
    
    return app, socketio