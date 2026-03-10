"""
Flask application factory and main application entry point.

This module creates and configures the Flask application instance
with WebSocket support for real-time game communication.
"""

import os

from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from loguru import logger

# Templates live at the repo root's templates/ directory, two levels above this file.
_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'templates')


def create_app(config=None):
    """
    Create and configure the Flask application.
    
    Args:
        config: Configuration object or dictionary
        
    Returns:
        Flask application instance
    """
    # Configure logging
    logger.remove()  # Remove default handler
    logger.add(
        lambda msg: print(msg),
        format="{time} | {level} | {message}",
        level="INFO",
        colorize=True
    )
    logger.info("Starting Grab game server")
    
    app = Flask(__name__, template_folder=_TEMPLATE_DIR)
    
    # Default configuration
    app.config.update({
        'SECRET_KEY': 'dev-key-change-in-production',
        'DEBUG': True,
        'GAME_TYPE': 'grab'
    })
    
    if config:
        app.config.update(config)
    
    # Enable CORS for all HTTP requests
    CORS(app, origins="*")
    
    # Initialize SocketIO for WebSocket support
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Register blueprints/routes here
    from . import routes
    app.register_blueprint(routes.bp)
    
    from . import api
    app.register_blueprint(api.api_bp)
    
    # Set the global socketio reference for API use
    api.socketio_instance = socketio
    
    # Initialize WebSocket handlers
    from . import websocket_handlers
    websocket_handlers.init_socketio_handlers(socketio)
    
    return app, socketio