/**
 * GameInterface component provides the main game view for active games.
 * Combines all game components and handles the overall game layout and state management.
 */
import React, { useState, useEffect } from 'react';
import LetterPool from './LetterPool';
import PlayerWords from './PlayerWords';
import WordInput from './WordInput';
import GameLog from './GameLog';

function GameInterface({ 
  gameState, 
  socket, 
  currentUsername,
  authToken,
  serverUrl,
  gameEvents,
  gameCreator,
  onAddGameEvent,
  onLeaveGame 
}) {
  const [hasShownWelcome, setHasShownWelcome] = useState(false);

  // Add initial welcome message (only once per game)
  useEffect(() => {
    if (gameState && onAddGameEvent && !hasShownWelcome) {
      onAddGameEvent('system', `Welcome to game ${gameState.game_id}! Type a word to play or !ready to pass.`);
      setHasShownWelcome(true);
    }
  }, [gameState?.game_id, onAddGameEvent, hasShownWelcome]);

  // Handle word submission
  const handleSubmitWord = (word) => {
    if (!socket || !word.trim()) return;

    if (onAddGameEvent) {
      onAddGameEvent('move', `Attempting to make word: "${word.toUpperCase()}"`);
    }
    
    socket.emit('move', { data: word.toLowerCase() });
  };

  // Handle pass/ready action
  const handlePass = () => {
    if (!socket) return;

    if (onAddGameEvent) {
      onAddGameEvent('move', 'Signaling ready for next turn...');
    }
    
    socket.emit('player_action', { data: 'ready_for_next_turn' });
  };

  // Handle starting the game (creator only)
  const handleStartGame = async () => {
    if (!authToken || !gameState?.game_id) return;

    if (onAddGameEvent) {
      onAddGameEvent('system', 'Starting game...');
    }

    try {
      const response = await fetch(`${serverUrl}/api/games/${gameState.game_id}/start`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to start game: ${response.status}`);
      }

      const result = await response.json();
      if (result.success && onAddGameEvent) {
        onAddGameEvent('success', 'Game started successfully! First turn beginning...');
      } else if (onAddGameEvent) {
        onAddGameEvent('error', result.error || 'Failed to start game');
      }
    } catch (error) {
      if (onAddGameEvent) {
        onAddGameEvent('error', `Error starting game: ${error.message}`);
      }
    }
  };

  // Handle leaving game
  const handleLeaveGame = () => {
    if (onLeaveGame) {
      onLeaveGame();
    }
  };

  if (!gameState) {
    return (
      <div className="game-interface" style={{ padding: '20px', color: '#fff' }}>
        <div style={{ textAlign: 'center', color: '#888' }}>
          Loading game...
        </div>
      </div>
    );
  }

  // Parse game state
  let parsedState = {};
  try {
    parsedState = typeof gameState.state === 'string' ? JSON.parse(gameState.state) : gameState.state;
  } catch (e) {
    console.error('Failed to parse game state:', e);
    parsedState = { pool: [], words_per_player: [], scores: [] };
  }

  const isGameActive = gameState.status === 'active';
  const isGameWaiting = gameState.status === 'waiting';
  const pool = parsedState.pool || [];
  
  // Check if current user is the game creator - use tracked creator
  const isCreator = gameCreator === currentUsername;
    
  // Debug logging for creator detection
  console.log('Creator detection debug:', {
    currentUsername,
    gameCreator,
    isCreator,
    isGameWaiting
  });

  return (
    <div className="game-interface" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Game Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '20px',
        backgroundColor: '#222',
        padding: '15px',
        borderRadius: '8px'
      }}>
        <div>
          <h1 style={{ margin: 0, color: '#fff', fontSize: '24px' }}>
            🎮 Game {gameState.game_id}
          </h1>
          <div style={{ color: '#aaa', fontSize: '14px', marginTop: '5px' }}>
            Status: <span style={{ 
              color: isGameActive ? '#28a745' : '#ffa500',
              fontWeight: 'bold'
            }}>
              {gameState.status?.toUpperCase() || 'UNKNOWN'}
            </span>
            {gameState.current_turn && (
              <span> • Turn: {gameState.current_turn}</span>
            )}
            {gameState.turn_time_remaining && (
              <span> • Time: {gameState.turn_time_remaining}s</span>
            )}
          </div>
        </div>
        
        <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
          <div style={{ textAlign: 'right', color: '#aaa', fontSize: '12px' }}>
            Playing as: <strong style={{ color: '#00ff00' }}>{currentUsername}</strong>
            {isCreator && <div style={{ color: '#ffd700', fontSize: '11px' }}>👑 Game Creator</div>}
          </div>
          
          <button
            onClick={handleLeaveGame}
            style={{
              padding: '8px 16px',
              backgroundColor: '#dc3545',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            🚪 Leave Game
          </button>
        </div>
      </div>

      {/* Prominent Start Game Button for waiting games */}
      {isGameWaiting && (
        <div style={{
          backgroundColor: isCreator ? '#1a4a1a' : '#444',
          border: isCreator ? '2px solid #28a745' : '1px solid #666',
          borderRadius: '8px',
          padding: '20px',
          textAlign: 'center',
          marginBottom: '20px'
        }}>
          <h3 style={{ color: '#fff', margin: '0 0 15px 0' }}>
            🎮 Game Ready to Start
          </h3>
          
          {isCreator ? (
            <div>
              <p style={{ color: '#aaa', margin: '0 0 15px 0' }}>
                You are the game creator. Click the button below to begin the game!
              </p>
              <button
                onClick={handleStartGame}
                style={{
                  padding: '15px 30px',
                  backgroundColor: '#28a745',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '18px',
                  fontWeight: 'bold',
                  boxShadow: '0 4px 8px rgba(40, 167, 69, 0.3)'
                }}
              >
                🎯 START GAME
              </button>
            </div>
          ) : (
            <div>
              <p style={{ color: '#aaa', margin: '0' }}>
                Waiting for the game creator to start the game...
              </p>
              <div style={{ color: '#666', fontSize: '14px', marginTop: '10px' }}>
                Game will begin automatically when started
              </div>
            </div>
          )}
        </div>
      )}

      {/* Main Game Layout */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: '1fr 1fr', 
        gap: '20px',
        '@media (max-width: 768px)': {
          gridTemplateColumns: '1fr'
        }
      }}>
        {/* Left Column - Game State */}
        <div className="game-state-column">
          <LetterPool pool={pool} />
          <PlayerWords 
            players={gameState.players}
            gameState={gameState}
            currentUsername={currentUsername}
          />
        </div>

        {/* Right Column - Input and Log */}
        <div className="game-interaction-column">
          <WordInput
            onSubmitWord={handleSubmitWord}
            onPass={handlePass}
            disabled={!isGameActive || !socket}
            gameId={gameState.game_id}
            currentUsername={currentUsername}
          />
          <GameLog 
            messages={gameEvents || []}
            maxMessages={50}
            autoScroll={true}
          />
        </div>
      </div>

      {/* Game Status Messages */}
      {!isGameActive && (
        <div style={{
          marginTop: '20px',
          padding: '15px',
          backgroundColor: '#444',
          borderRadius: '8px',
          textAlign: 'center',
          color: '#ffa500'
        }}>
          <strong>Game is not active.</strong> 
          {gameState.status === 'waiting' && (
            isCreator 
              ? ' Click "Start Game" to begin!' 
              : ' Waiting for game creator to start the game.'
          )}
          {gameState.status === 'finished' && ' Game has ended.'}
        </div>
      )}

      {/* Instructions */}
      <div style={{
        marginTop: '20px',
        padding: '15px',
        backgroundColor: '#111',
        border: '1px solid #333',
        borderRadius: '8px',
        fontSize: '12px',
        color: '#666'
      }}>
        <strong>How to Play:</strong>
        <ul style={{ margin: '8px 0', paddingLeft: '20px' }}>
          <li>Form words using available letters from the pool and/or other players' words</li>
          <li>You can steal one existing word from any player to create a new word</li>
          <li>Type your word in the command input and press Enter</li>
          <li>Use <code style={{backgroundColor: '#333', padding: '1px 4px'}}>!ready</code> when you can't make any more words</li>
          <li>Game advances to the next turn when all players are ready</li>
        </ul>
      </div>
    </div>
  );
}

export default GameInterface;