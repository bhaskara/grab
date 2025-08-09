/**
 * GameOverScreen component displays the final game results with a prominent "Game Over!" message.
 * Shows final scores, winner, and automatically returns to lobby after a delay.
 */
import React, { useState, useEffect } from 'react';

function GameOverScreen({ gameOverData, currentUsername, onReturnToLobby }) {
  const [countdown, setCountdown] = useState(5);

  // Countdown timer
  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  if (!gameOverData) {
    return null;
  }

  const { reason, final_scores, winner, final_game_state } = gameOverData;
  
  // Parse final scores and sort by score
  const sortedScores = Object.entries(final_scores)
    .sort(([,a], [,b]) => b - a)
    .map(([player, score], index) => ({
      player,
      score,
      rank: index + 1
    }));

  const isWinner = winner === currentUsername;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.9)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#fff',
      fontFamily: 'monospace',
      zIndex: 1000
    }}>
      {/* Large Game Over Message */}
      <div style={{
        fontSize: '4rem',
        fontWeight: 'bold',
        color: '#ff6b6b',
        textShadow: '0 0 20px rgba(255, 107, 107, 0.5)',
        marginBottom: '30px',
        animation: 'pulse 2s infinite',
        textAlign: 'center'
      }}>
        🎮 GAME OVER! 🎮
      </div>

      {/* Winner announcement */}
      {winner && (
        <div style={{
          fontSize: '2rem',
          fontWeight: 'bold',
          color: isWinner ? '#ffd700' : '#90EE90',
          textShadow: '0 0 15px rgba(255, 215, 0, 0.5)',
          marginBottom: '30px',
          textAlign: 'center'
        }}>
          {isWinner ? '🏆 YOU WON! 🏆' : `🏆 ${winner} WINS! 🏆`}
        </div>
      )}

      {/* Game ending reason */}
      <div style={{
        fontSize: '1.2rem',
        color: '#aaa',
        marginBottom: '40px',
        textAlign: 'center'
      }}>
        Game ended: {reason}
      </div>

      {/* Final Scores */}
      <div style={{
        backgroundColor: '#222',
        borderRadius: '12px',
        padding: '30px',
        maxWidth: '600px',
        width: '90%',
        border: '2px solid #444'
      }}>
        <h2 style={{
          textAlign: 'center',
          color: '#ffd700',
          marginBottom: '25px',
          fontSize: '1.5rem'
        }}>
          Final Scores
        </h2>

        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          {sortedScores.map(({ player, score, rank }) => {
            const isCurrentPlayer = player === currentUsername;
            const isFirstPlace = rank === 1;
            
            return (
              <div
                key={player}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  backgroundColor: isCurrentPlayer ? '#1a4a1a' : '#333',
                  border: isCurrentPlayer 
                    ? '2px solid #28a745' 
                    : isFirstPlace 
                      ? '2px solid #ffd700' 
                      : '1px solid #555',
                  borderRadius: '8px',
                  padding: '15px 20px',
                  fontSize: '1.1rem'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                  <div style={{
                    fontSize: '1.2rem',
                    color: isFirstPlace ? '#ffd700' : '#aaa',
                    fontWeight: 'bold',
                    width: '30px'
                  }}>
                    #{rank}
                  </div>
                  <div style={{
                    color: isCurrentPlayer ? '#90EE90' : '#fff',
                    fontWeight: 'bold'
                  }}>
                    {player}
                    {isCurrentPlayer && ' (You)'}
                    {isFirstPlace && ' 👑'}
                  </div>
                </div>
                <div style={{
                  fontSize: '1.3rem',
                  fontWeight: 'bold',
                  color: '#ffd700',
                  backgroundColor: '#444',
                  padding: '8px 16px',
                  borderRadius: '20px'
                }}>
                  {score} pts
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Countdown and Return Button */}
      <div style={{
        marginTop: '40px',
        textAlign: 'center',
        fontSize: '1.1rem',
        color: '#aaa'
      }}>
        <div style={{ marginBottom: '15px' }}>
          Returning to lobby in {countdown} seconds...
        </div>
        <button
          onClick={onReturnToLobby}
          style={{
            padding: '12px 30px',
            fontSize: '1rem',
            backgroundColor: '#28a745',
            color: '#fff',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
          onMouseOver={(e) => e.target.style.backgroundColor = '#218838'}
          onMouseOut={(e) => e.target.style.backgroundColor = '#28a745'}
        >
          Return to Lobby Now
        </button>
      </div>

      {/* CSS Animation */}
      <style jsx>{`
        @keyframes pulse {
          0% { transform: scale(1); }
          50% { transform: scale(1.05); }
          100% { transform: scale(1); }
        }
      `}</style>
    </div>
  );
}

export default GameOverScreen;