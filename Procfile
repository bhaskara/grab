# Procfile — used by honcho to start both servers with a single command.
#
# Usage:
#   honcho start
#
# Prerequisites:
#   pip install honcho          (or: pip install -r requirements.txt)
#   cp .env.example .env        (then set SECRET_KEY in .env)
#
# BROWSER=none prevents React from auto-opening a browser tab on macOS.
# Both servers run from the repo root; the React process cd's into web/ first.

web:   python run.py
react: cd web && BROWSER=none PORT=3000 npm start
