# Dockerfile for deploying the Grab game server to Railway.
#
# Multi-stage build:
# 1. Build stage: installs Node.js deps and builds the React frontend
# 2. Runtime stage: installs Python deps and serves the app with gunicorn
#
# Usage (local testing):
#   docker build -t grab .
#   docker run -p 5001:5001 -e PORT=5001 -e SECRET_KEY=dev grab

# --- Stage 1: Build React frontend ---
FROM node:20-slim AS frontend-build

WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm install
COPY web/ ./
RUN npm run build

# --- Stage 2: Python runtime ---
FROM python:3.13-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy React build from stage 1
COPY --from=frontend-build /app/web/build ./web/build

# Railway sets PORT automatically; default to 5001 for local testing
ENV PORT=5001

EXPOSE ${PORT}

CMD ["sh", "-c", "gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 --bind 0.0.0.0:$PORT wsgi:app"]
