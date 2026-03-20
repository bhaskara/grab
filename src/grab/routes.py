"""
Flask routes for the web interface.

In production (when web/build/ exists), routes serve the React single-page
app's index.html. In development, Jinja templates are served instead so
the React dev server can run separately.
"""

import os

from flask import Blueprint, render_template, send_from_directory

# Check at import time whether a React production build exists.
_REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
_REACT_BUILD_DIR = os.path.join(_REPO_ROOT, 'web', 'build')
_SERVE_REACT = os.path.isfile(os.path.join(_REACT_BUILD_DIR, 'index.html'))

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """
    Main page.

    Serves web/build/index.html in production, or the Jinja
    index.html template in development.
    """
    if _SERVE_REACT:
        return send_from_directory(_REACT_BUILD_DIR, 'index.html')
    return render_template('index.html')


@bp.route('/game/<game_id>')
def game(game_id):
    """
    Game room page.

    Parameters
    ----------
    game_id : str
        The unique identifier of the game to display.

    Returns
    -------
    Response
        The React SPA index.html in production, or the Jinja
        game.html template in development.
    """
    if _SERVE_REACT:
        return send_from_directory(_REACT_BUILD_DIR, 'index.html')
    return render_template('game.html', game_id=game_id)