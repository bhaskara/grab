/**
 * PlayerWords component displays all players' current words and scores.
 * Shows each player's word collection with individual word scores and total scores.
 */
import React from 'react';

// Scrabble letter point values
const LETTER_POINTS = {
  'a': 1, 'b': 3, 'c': 3, 'd': 2, 'e': 1, 'f': 4, 'g': 2, 'h': 4, 'i': 1, 'j': 8,
  'k': 5, 'l': 1, 'm': 3, 'n': 1, 'o': 1, 'p': 3, 'q': 10, 'r': 1, 's': 1, 't': 1,
  'u': 1, 'v': 4, 'w': 4, 'x': 8, 'y': 4, 'z': 10
};

function PlayerWords({ players, gameState, currentUsername, finalScores = null }) {
  if (!players || !gameState) {
    return (
      <div className="player-words" style={{ padding: '15px', backgroundColor: '#222', borderRadius: '8px', margin: '10px 0' }}>
        <h3 style={{ margin: '0 0 10px 0', color: '#fff' }}>👥 Players</h3>
        <div style={{ color: '#888', fontStyle: 'italic' }}>No game data available</div>
      </div>
    );
  }

  // Calculate word score
  const calculateWordScore = (word) => {
    return word.toLowerCase().split('').reduce((sum, letter) => {
      return sum + (LETTER_POINTS[letter] || 0);
    }, 0);
  };

  // Parse game state to get words per player
  let parsedState = {};
  try {
    parsedState = typeof gameState.state === 'string' ? JSON.parse(gameState.state) : gameState.state;
  } catch (e) {
    console.error('Failed to parse game state:', e);
    parsedState = { words_per_player: [], scores: [] };
  }

  const wordsPerPlayer = parsedState.words_per_player || [];
  const scores = parsedState.scores || [];
  
  // Get player usernames in order
  const playerNames = Object.keys(players);

  return (
    <div className="player-words" style={{ padding: '15px', backgroundColor: '#222', borderRadius: '8px', margin: '10px 0' }}>
      <h3 style={{ margin: '0 0 15px 0', color: '#fff' }}>👥 Players</h3>
      
      <div className="players-container" style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {playerNames.map((username, playerIndex) => {
          const playerData = players[username];
          const playerWords = wordsPerPlayer[playerIndex] || [];
          // Use final scores if available (game ended), otherwise use current scores
          const playerScore = finalScores 
            ? (finalScores[username] || 0)
            : (scores[playerIndex] || playerData?.score || 0);
          const isCurrentPlayer = username === currentUsername;
          const isConnected = playerData?.connected !== false;
          
          return (
            <div 
              key={username} 
              className="player-section"
              style={{
                backgroundColor: isCurrentPlayer ? '#1a4a1a' : '#333',
                border: isCurrentPlayer ? '2px solid #28a745' : '1px solid #555',
                borderRadius: '8px',
                padding: '12px'
              }}
            >
              <div className="player-header" style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginBottom: '10px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ 
                    fontSize: '16px', 
                    fontWeight: 'bold',
                    color: isCurrentPlayer ? '#90EE90' : '#fff'
                  }}>
                    {username}
                    {isCurrentPlayer && ' (You)'}
                  </span>
                  <span style={{ 
                    fontSize: '12px',
                    color: isConnected ? '#28a745' : '#dc3545',
                    fontWeight: 'bold'
                  }}>
                    {isConnected ? '● Online' : '● Offline'}
                  </span>
                </div>
                <div style={{
                  fontSize: '18px',
                  fontWeight: 'bold',
                  color: '#ffd700',
                  backgroundColor: '#444',
                  padding: '4px 12px',
                  borderRadius: '15px'
                }}>
                  {playerScore} pts
                </div>
              </div>
              
              <div className="player-words-list" style={{ minHeight: '30px' }}>
                {playerWords.length === 0 ? (
                  <div style={{ 
                    color: '#888', 
                    fontStyle: 'italic',
                    textAlign: 'center',
                    padding: '10px'
                  }}>
                    No words yet
                  </div>
                ) : (
                  <div className="words-grid" style={{ 
                    display: 'flex', 
                    flexWrap: 'wrap', 
                    gap: '8px' 
                  }}>
                    {playerWords.map((word, wordIndex) => {
                      const wordScore = calculateWordScore(word);
                      return (
                        <div 
                          key={`${word}-${wordIndex}`}
                          className="word-chip"
                          style={{
                            backgroundColor: '#444',
                            border: '1px solid #666',
                            borderRadius: '20px',
                            padding: '6px 12px',
                            fontSize: '14px',
                            color: '#fff',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px'
                          }}
                        >
                          <span style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                            {word.toUpperCase()}
                          </span>
                          <span style={{ 
                            fontSize: '12px', 
                            color: '#ffd700',
                            backgroundColor: '#333',
                            borderRadius: '10px',
                            padding: '1px 6px'
                          }}>
                            {wordScore}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      
      {playerNames.length === 0 && (
        <div style={{ 
          color: '#888', 
          fontStyle: 'italic',
          textAlign: 'center',
          padding: '20px'
        }}>
          No players in game
        </div>
      )}
    </div>
  );
}

export default PlayerWords;