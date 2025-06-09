"""
Flask routes and WebSocket event handlers.

This module defines HTTP routes for the web interface and
WebSocket event handlers for real-time game communication.
"""

from flask import Blueprint, render_template, request
from flask_socketio import emit, join_room, leave_room

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Main game page."""
    return render_template('index.html')

@bp.route('/game/<game_id>')
def game(game_id):
    """Game room page."""
    return render_template('game.html', game_id=game_id)