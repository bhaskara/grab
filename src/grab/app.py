"""
Flask application factory and main application entry point.

This module creates and configures the Flask application instance
with WebSocket support for real-time game communication.

In production, Flask also serves the React static build from web/build/.
In development (when web/build/ doesn't exist), Jinja templates are served
and the React dev server runs separately.
"""

import os

from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
from loguru import logger

# Repo root is two levels above this file (src/grab/app.py -> repo root)
_REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')

# Templates live at the repo root's templates/ directory.
_TEMPLATE_DIR = os.path.join(_REPO_ROOT, 'templates')

# React production build directory.
_REACT_BUILD_DIR = os.path.join(_REPO_ROOT, 'web', 'build')


def _has_react_build():
    """
    Check whether a React production build exists at web/build/.

    Returns
    -------
    bool
        True if web/build/index.html exists (production mode),
        False otherwise (development mode).
    """
    return os.path.isfile(os.path.join(_REACT_BUILD_DIR, 'index.html'))


def create_app(config=None):
    """
    Create and configure the Flask application.

    In production (when web/build/ exists), Flask serves the React static
    build. In development, Jinja templates are served instead.

    Parameters
    ----------
    config : dict, optional
        Configuration overrides to apply on top of defaults.

    Returns
    -------
    tuple
        (Flask app, SocketIO instance)
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

    serve_react = _has_react_build()

    # When serving the React build, point Flask's static_folder at
    # web/build/static so that /static/js/..., /static/css/... work.
    if serve_react:
        logger.info("React build found — serving production frontend")
        app = Flask(
            __name__,
            template_folder=_TEMPLATE_DIR,
            static_folder=os.path.join(_REACT_BUILD_DIR, 'static'),
            static_url_path='/static',
        )
    else:
        logger.info("No React build — using Jinja templates (dev mode)")
        app = Flask(__name__, template_folder=_TEMPLATE_DIR)

    # Default configuration: read SECRET_KEY from env (fall back to dev
    # default) and default DEBUG to False (production-safe). Local dev
    # passes debug=True via run.py directly.
    app.config.update({
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-key-change-in-production'),
        'DEBUG': os.environ.get('FLASK_DEBUG', 'false').lower() in ('true', '1', 'yes'),
        'GAME_TYPE': 'grab',
    })

    if config:
        app.config.update(config)

    # Enable CORS for all HTTP requests (harmless in production where
    # everything is same-origin; still needed for local dev with separate ports).
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

    # --- Serve React build root-level files (manifest.json, favicon, etc.) ---
    if serve_react:
        @app.route('/manifest.json')
        def serve_manifest():
            """Serve the React app manifest."""
            return send_from_directory(_REACT_BUILD_DIR, 'manifest.json')

        @app.route('/favicon.ico')
        def serve_favicon():
            """Serve the favicon."""
            return send_from_directory(_REACT_BUILD_DIR, 'favicon.ico')

        @app.route('/robots.txt')
        def serve_robots():
            """Serve robots.txt."""
            return send_from_directory(_REACT_BUILD_DIR, 'robots.txt')

        @app.route('/logo192.png')
        def serve_logo192():
            """Serve the 192px logo."""
            return send_from_directory(_REACT_BUILD_DIR, 'logo192.png')

        @app.route('/logo512.png')
        def serve_logo512():
            """Serve the 512px logo."""
            return send_from_directory(_REACT_BUILD_DIR, 'logo512.png')

    return app, socketio