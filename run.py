"""
Development server entry point.

Run this script to start the Flask development server with WebSocket support.

Usage:
    python run.py [--port PORT] [--host HOST]
"""

import argparse

from src.grab.app import create_app


def parse_args():
    """Parse command-line arguments.

    Returns
    -------
    argparse.Namespace
        Parsed arguments with `host` and `port` attributes.
    """
    parser = argparse.ArgumentParser(description='Run the Grab game development server.')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5001, help='Port to listen on (default: 5001)')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    app, socketio = create_app()
    socketio.run(app, debug=True, host=args.host, port=args.port, allow_unsafe_werkzeug=True)