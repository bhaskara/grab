"""
Development server entry point.

Run this script to start the Flask development server with WebSocket support.
"""

from src.grab.app import create_app

if __name__ == '__main__':
    app, socketio = create_app()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)