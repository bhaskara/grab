# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a web-based implementation of "Grab" - a word game played with Scrabble tiles. The game uses an authoritative server model where clients connect via WebSocket to a Flask server that maintains all game state in-memory.

## Architecture

**Server**: Flask-based with WebSocket connections for real-time communication. Game state is maintained in-memory within the Flask process. Each game has a unique ID and supports multiple concurrent games.

**Client-Server Model**: 
- Clients send moves to the server
- Server validates moves and broadcasts state updates
- Bidirectional WebSocket communication for low-latency gameplay
- Timer mechanism per game for turn progression and time limits

**Game Flow**:
1. Players join via web browser and enter names
2. First player creates new game (gets unique ID)
3. Other players join using the game ID
4. Game starts when first player initiates
5. Players form words by typing and pressing enter
6. Server validates and updates state for all players

## Key Requirements

- **Real-time gameplay**: State updates should reflect within a few hundred milliseconds
- **Word validation**: Server validates all word attempts before applying changes
- **Turn-based progression**: Automatic turn advancement via timer when no moves possible
- **Multi-game support**: Server handles multiple concurrent games via unique IDs
- **Scoring system**: Points based on Scrabble tile values with end-game bonuses

## Project Status

Currently in prototype phase - not designed for large scale deployment. Focus is on core gameplay mechanics and real-time communication patterns.