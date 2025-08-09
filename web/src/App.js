import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import GameLobby from './GameLobby';
import GameInterface from './GameInterface';
import './App.css';

function App() {
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('Ready to login');
  const [serverUrl, setServerUrl] = useState('');
  const [authToken, setAuthToken] = useState(null);
  const [username, setUsername] = useState('');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentGameId, setCurrentGameId] = useState(null);
  const [showLobby, setShowLobby] = useState(false);
  const [gameState, setGameState] = useState(null);
  const [inGame, setInGame] = useState(false);
  const [gameEvents, setGameEvents] = useState([]);
  const [gameCreator, setGameCreator] = useState(null);

  // Generate random username on component mount
  useEffect(() => {
    const randomUsername = `user${Math.floor(Math.random() * 10000)}`;
    setUsername(randomUsername);
    
    // Determine server URL
    const serverUrl = window.location.hostname === 'localhost' 
      ? 'http://localhost:5000'  // Local development
      : `http://${window.location.hostname}:5000`;  // External access
    
    setServerUrl(serverUrl);
    console.log('Server URL:', serverUrl);
    console.log('Generated random username:', randomUsername);
  }, []);

  const loginAndConnect = async () => {
    if (!username) return;
    
    setConnectionStatus('Logging in...');
    
    // Step 1: Login to get auth token
    try {
      const response = await fetch(`${serverUrl}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username })
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        setConnectionStatus(`Login failed: ${response.status}`);
        return;
      }
      
      const result = await response.json();
      if (!result.success) {
        setConnectionStatus(`Login failed: ${result.error}`);
        return;
      }

      // Login successful, set auth token and update state
      const token = result.data.session_token;
      setAuthToken(token);
      setIsLoggedIn(true);
      console.log('Login successful for', username);
      
      // Step 2: Immediately connect to Socket.IO
      setConnectionStatus('Connecting to game server...');
      
      if (socket) {
        socket.disconnect();
      }
      
      const newSocket = io(serverUrl, {
        auth: { token: token },
        autoConnect: false
      });

      newSocket.on('connect', () => {
        setConnected(true);
        setConnectionStatus('Connected successfully!');
        console.log('Socket.IO connected successfully');
      });

      newSocket.on('disconnect', () => {
        setConnected(false);
        setConnectionStatus('Disconnected');
        console.log('Socket.IO disconnected');
      });

      newSocket.on('error', (error) => {
        setConnectionStatus('Socket Error: ' + error);
        console.error('Socket.IO error:', error);
      });

      newSocket.on('connect_error', (error) => {
        setConnectionStatus('Connection Error: ' + error.message);
        console.error('Socket.IO connection error:', error);
      });

      newSocket.on('connected', (data) => {
        console.log('Server confirmed connection:', data);
        // After successful socket connection, show the lobby
        setShowLobby(true);
      });

      // Game state updates
      newSocket.on('game_state', (data) => {
        console.log('Game state update:', data);
        setGameState(data.data);
        setInGame(true);
        setShowLobby(false);
      });

      // Move results
      newSocket.on('move_result', (data) => {
        console.log('Move result:', data);
        if (data.success && data.game_state) {
          setGameState(data.game_state);
          addGameEvent('success', 'Move successful!');
        } else if (data.error) {
          addGameEvent('error', `Move failed: ${data.error}`);
        }
      });

      // Player connection events
      newSocket.on('player_disconnected', (data) => {
        console.log('Player disconnected:', data);
        addGameEvent('connection', `${data.player} disconnected`);
      });

      newSocket.on('player_reconnected', (data) => {
        console.log('Player reconnected:', data);
        addGameEvent('connection', `${data.player} reconnected`);
      });

      // Game ended event
      newSocket.on('game_ended', (data) => {
        console.log('Game ended:', data);
        addGameEvent('game_event', `Game ended by ${data.ended_by}: ${data.reason}`);
        setInGame(false);
        setGameState(null);
        setCurrentGameId(null);
        setShowLobby(true);
      });

      // Turn progression events
      newSocket.on('turn_starting', (data) => {
        console.log('Turn starting:', data);
        const letters = data.letters_drawn ? data.letters_drawn.join(', ').toUpperCase() : 'none';
        addGameEvent('game_event', `Turn ${data.turn_number} starting! New letters: ${letters} (${data.letters_remaining_in_bag} left in bag)`);
        if (data.time_limit) {
          addGameEvent('system', `Turn timer: ${data.time_limit} seconds`);
        }
      });

      newSocket.on('turn_ending', (data) => {
        console.log('Turn ending:', data);
        const reason = data.reason === 'all_players_passed' ? 'All players passed' : 'Time expired';
        addGameEvent('game_event', `Turn ${data.turn_number} ended: ${reason} (${data.final_moves_count} moves made)`);
      });

      newSocket.on('game_ending', (data) => {
        console.log('Game ending:', data);
        const reason = data.reason === 'bag_empty' ? 'All letters used' : 'Game stopped by creator';
        addGameEvent('game_event', `Game ending: ${reason}`);
        
        if (data.final_scores) {
          const scores = Object.entries(data.final_scores)
            .sort(([,a], [,b]) => b - a)
            .map(([player, score]) => `${player}: ${score}`)
            .join(', ');
          addGameEvent('success', `Final scores: ${scores}`);
          
          if (data.winner) {
            addGameEvent('success', `🏆 Winner: ${data.winner}!`);
          }
        }
      });

      setSocket(newSocket);
      newSocket.connect();
      
    } catch (error) {
      if (isLoggedIn) {
        setConnectionStatus(`Connection error: ${error.message}`);
      } else {
        setConnectionStatus(`Login error: ${error.message}`);
      }
    }
  };

  const disconnect = () => {
    if (socket) {
      socket.disconnect();
      setSocket(null);
    }
    setConnected(false);
    setIsLoggedIn(false);
    setAuthToken(null);
    setConnectionStatus('Disconnected');
    setShowLobby(false);
    setCurrentGameId(null);
    setGameState(null);
    setInGame(false);
    setGameEvents([]);
    setGameCreator(null);
  };

  const handleGameJoined = (gameId, joinData) => {
    setCurrentGameId(gameId);
    console.log('Joined game:', gameId, joinData);
    // Game state will be received via game_state socket event
    // which will automatically switch to game view
  };

  const handleGameCreated = (gameId) => {
    console.log('Created game:', gameId);
    // Track that current user created this game
    setGameCreator(username);
  };

  const handleLeaveGame = () => {
    setInGame(false);
    setGameState(null);
    setCurrentGameId(null);
    setGameEvents([]);
    setGameCreator(null);
    setShowLobby(true);
  };

  // Helper function to add game events
  const addGameEvent = (type, text) => {
    const event = {
      timestamp: Date.now(),
      type: type,
      text: text
    };
    setGameEvents(prev => [...prev, event]);
  };

  // Show game interface if in a game
  if (inGame && gameState && connected && isLoggedIn) {
    return (
      <div className="App">
        <GameInterface 
          gameState={gameState}
          socket={socket}
          currentUsername={username}
          authToken={authToken}
          serverUrl={serverUrl}
          gameEvents={gameEvents}
          gameCreator={gameCreator}
          onAddGameEvent={addGameEvent}
          onLeaveGame={handleLeaveGame}
        />
      </div>
    );
  }

  // Show lobby if connected and authenticated
  if (showLobby && connected && isLoggedIn) {
    return (
      <div className="App">
        <header className="App-header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h1>🎮 Grab Game - Web Frontend</h1>
              <p>Step 4: Terminal-like Game Interface ✅</p>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ color: '#aaa', fontSize: '14px' }}>
                Logged in as: <strong>{username}</strong>
              </div>
              <div style={{ color: 'lime', fontSize: '12px' }}>
                ● Connected to {serverUrl}
              </div>
              <button 
                onClick={disconnect}
                style={{ 
                  padding: '6px 12px', 
                  fontSize: '12px', 
                  backgroundColor: '#dc3545',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '3px',
                  cursor: 'pointer',
                  marginTop: '5px'
                }}
              >
                Disconnect
              </button>
            </div>
          </div>
          
          <GameLobby 
            serverUrl={serverUrl}
            authToken={authToken}
            onGameJoined={handleGameJoined}
            onGameCreated={handleGameCreated}
          />
        </header>
      </div>
    );
  }

  // Show authentication/connection flow
  return (
    <div className="App">
      <header className="App-header">
        <h1>🎮 Grab Game - Web Frontend</h1>
        <p>Step 4: Terminal-like Game Interface</p>
        
        <div style={{ margin: '20px', padding: '20px', background: '#444', borderRadius: '8px' }}>
          <p><strong>Server URL:</strong> <code>{serverUrl || 'Loading...'}</code></p>
          <p><strong>Username:</strong> <code>{username}</code></p>
          <p><strong>Status:</strong> <span style={{ 
            color: connected ? 'lime' : (isLoggedIn ? 'orange' : 'white'),
            fontWeight: 'bold' 
          }}>
            {connectionStatus}
          </span></p>
        </div>
        
        <div style={{ margin: '20px' }}>
          {(!isLoggedIn || !connected) ? (
            <button 
              onClick={loginAndConnect}
              style={{ padding: '12px 24px', fontSize: '16px', marginRight: '10px' }}
            >
              🎮 Join Game Lobby as {username}
            </button>
          ) : (
            <button 
              onClick={disconnect}
              style={{ padding: '12px 24px', fontSize: '16px', marginRight: '10px' }}
            >
              Disconnect
            </button>
          )}
        </div>

        <div style={{ marginTop: '30px', fontSize: '14px', textAlign: 'left', maxWidth: '600px' }}>
          <h3>Progress Checklist</h3>
          <ul>
            <li>✅ React app created and running</li>
            <li>✅ Socket.IO client library installed</li>
            <li>✅ Random username generation</li>
            <li>✅ HTTP API authentication working</li>
            <li>✅ CORS configured for cross-origin requests</li>
            <li>{connected ? '✅' : '⏳'} Socket.IO connection with JWT auth</li>
            <li>{showLobby ? '✅' : '⏳'} Game lobby interface</li>
            <li>{inGame ? '✅' : '⏳'} Terminal-like game interface</li>
          </ul>
          
          <div style={{ marginTop: '20px', padding: '10px', background: '#333', borderRadius: '4px' }}>
            <strong>Current Step:</strong> Step 4 - Terminal-like Game Interface<br/>
            <strong>Next:</strong> {inGame ? 'Step 5 - Real-time Features' : (showLobby ? 'Join a game to test' : 'Click the button above to join the game lobby')}
          </div>
        </div>
      </header>
    </div>
  );
}

export default App;
// DEBUG: File modified at Thu Aug  7 22:21:19 UTC 2025
