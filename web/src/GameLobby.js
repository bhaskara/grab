/**
 * GameLobby component handles the game lobby interface.
 * Shows list of available games, allows creating new games, and joining existing ones.
 */
import React, { useState, useEffect } from 'react';

function GameLobby({ serverUrl, authToken, onGameJoined }) {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);

  // Fetch games list
  const fetchGames = async () => {
    try {
      const response = await fetch(`${serverUrl}/api/games`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch games: ${response.status}`);
      }

      const result = await response.json();
      if (result.success) {
        setGames(result.data.games || []);
        setError('');
      } else {
        setError(result.error || 'Failed to fetch games');
      }
    } catch (err) {
      setError(`Error fetching games: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Create new game
  const createGame = async () => {
    if (creating) return;
    
    setCreating(true);
    setError('');

    try {
      const response = await fetch(`${serverUrl}/api/games`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          max_players: 4,
          time_limit_seconds: 300
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to create game: ${response.status}`);
      }

      const result = await response.json();
      if (result.success) {
        // Refresh games list to show the new game
        await fetchGames();
      } else {
        setError(result.error || 'Failed to create game');
      }
    } catch (err) {
      setError(`Error creating game: ${err.message}`);
    } finally {
      setCreating(false);
    }
  };

  // Join a game
  const joinGame = async (gameId) => {
    try {
      const response = await fetch(`${serverUrl}/api/games/${gameId}/join`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to join game: ${response.status}`);
      }

      const result = await response.json();
      if (result.success) {
        // Notify parent component that we joined a game
        if (onGameJoined) {
          onGameJoined(gameId, result.data);
        }
      } else {
        setError(result.error || 'Failed to join game');
      }
    } catch (err) {
      setError(`Error joining game: ${err.message}`);
    }
  };

  // Format date for display
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleTimeString();
  };

  // Get status color
  const getStatusColor = (status) => {
    switch (status) {
      case 'waiting': return '#ffa500'; // orange
      case 'active': return '#00ff00';  // green
      case 'finished': return '#888';   // gray
      default: return '#fff';
    }
  };

  // Load games on component mount and set up auto-refresh
  useEffect(() => {
    fetchGames();
    
    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchGames, 5000);
    
    return () => clearInterval(interval);
  }, [authToken]);

  return (
    <div className="game-lobby" style={{ padding: '20px', color: '#fff' }}>
      <h2>🎮 Game Lobby</h2>
      
      <div style={{ marginBottom: '20px' }}>
        <button 
          onClick={createGame}
          disabled={creating}
          style={{ 
            padding: '12px 24px', 
            fontSize: '16px', 
            backgroundColor: creating ? '#666' : '#007acc',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: creating ? 'not-allowed' : 'pointer'
          }}
        >
          {creating ? 'Creating...' : '➕ Create New Game'}
        </button>
        
        <button 
          onClick={fetchGames}
          disabled={loading}
          style={{ 
            padding: '12px 24px', 
            fontSize: '16px', 
            backgroundColor: '#444',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer',
            marginLeft: '10px'
          }}
        >
          {loading ? 'Refreshing...' : '🔄 Refresh'}
        </button>
      </div>

      {error && (
        <div style={{ 
          backgroundColor: '#ff4444', 
          color: '#fff', 
          padding: '10px', 
          borderRadius: '4px',
          marginBottom: '20px' 
        }}>
          ⚠️ {error}
        </div>
      )}

      <div className="games-list">
        <h3>Available Games ({games.length})</h3>
        
        {loading ? (
          <div style={{ color: '#888' }}>Loading games...</div>
        ) : games.length === 0 ? (
          <div style={{ color: '#888', fontStyle: 'italic' }}>
            No games available. Create one to get started!
          </div>
        ) : (
          <div className="games-table">
            {games.map(game => (
              <div 
                key={game.game_id} 
                className="game-item"
                style={{ 
                  backgroundColor: '#333',
                  border: '1px solid #555',
                  borderRadius: '8px',
                  padding: '15px',
                  marginBottom: '10px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
                      Game ID: <code style={{ backgroundColor: '#222', padding: '2px 6px', borderRadius: '3px' }}>
                        {game.game_id}
                      </code>
                    </div>
                    <div style={{ color: getStatusColor(game.status), marginTop: '5px' }}>
                      Status: <strong>{game.status.toUpperCase()}</strong>
                    </div>
                    <div style={{ color: '#ccc', fontSize: '14px', marginTop: '5px' }}>
                      Players: {game.current_players.length}/{game.max_players} | 
                      Created: {formatDate(game.created_at)}
                      {game.started_at && ` | Started: ${formatDate(game.started_at)}`}
                    </div>
                    {game.current_players.length > 0 && (
                      <div style={{ color: '#aaa', fontSize: '12px', marginTop: '5px' }}>
                        Players: {game.current_players.map(p => p.username).join(', ')}
                      </div>
                    )}
                  </div>
                  
                  <div>
                    {game.status === 'waiting' && (
                      <button
                        onClick={() => joinGame(game.game_id)}
                        style={{
                          padding: '8px 16px',
                          backgroundColor: '#28a745',
                          color: '#fff',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '14px'
                        }}
                      >
                        🚪 Join Game
                      </button>
                    )}
                    {game.status === 'active' && (
                      <span style={{ color: '#ffa500', fontSize: '14px' }}>
                        🎮 In Progress
                      </span>
                    )}
                    {game.status === 'finished' && (
                      <span style={{ color: '#888', fontSize: '14px' }}>
                        ✅ Finished
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ 
        marginTop: '30px', 
        padding: '15px', 
        backgroundColor: '#222', 
        borderRadius: '8px',
        fontSize: '14px',
        color: '#aaa'
      }}>
        <strong>Instructions:</strong>
        <ul style={{ marginTop: '10px', paddingLeft: '20px' }}>
          <li>Create a new game to start playing</li>
          <li>Join a waiting game to play with others</li>
          <li>Games automatically refresh every 5 seconds</li>
          <li>You need an active Socket.IO connection to join games</li>
        </ul>
      </div>
    </div>
  );
}

export default GameLobby;