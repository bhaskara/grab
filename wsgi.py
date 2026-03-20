"""
Production WSGI entry point for the Grab game server.

This module creates the Flask application and exposes it for gunicorn.
Usage: gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 --bind 0.0.0.0:$PORT wsgi:app

Note: Must use a single worker (-w 1) because all game state is stored
in-memory within the Flask process. Multiple workers would have separate
state copies.
"""

from src.grab.app import create_app

app, socketio = create_app()
