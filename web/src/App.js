import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import GameLobby from './GameLobby';
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

  const login = async () => {
    if (!username) return;
    
    setConnectionStatus('Logging in...');
    
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
      if (result.success) {
        setAuthToken(result.data.session_token);
        setIsLoggedIn(true);
        setConnectionStatus('Logged in - ready to connect');
        console.log('Login successful for', username);
      } else {
        setConnectionStatus(`Login failed: ${result.error}`);
      }
    } catch (error) {
      setConnectionStatus(`Login error: ${error.message}`);
    }
  };

  const connectSocket = () => {
    if (!authToken) {
      setConnectionStatus('Please login first');
      return;
    }
    
    if (socket) {
      socket.disconnect();
    }
    
    setConnectionStatus('Connecting...');
    
    const newSocket = io(serverUrl, {
      auth: { token: authToken },
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

    setSocket(newSocket);
    newSocket.connect();
  };

  const disconnect = () => {
    if (socket) {
      socket.disconnect();
      setSocket(null);
    }
    setConnected(false);
    setConnectionStatus('Disconnected');
    setShowLobby(false);
    setCurrentGameId(null);
  };

  const handleGameJoined = (gameId, joinData) => {
    setCurrentGameId(gameId);
    console.log('Joined game:', gameId, joinData);
    // TODO: Switch to game view in Step 4
  };

  // Show lobby if connected and authenticated
  if (showLobby && connected && isLoggedIn) {
    return (
      <div className="App">
        <header className="App-header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h1>🎮 Grab Game - Web Frontend</h1>
              <p>Step 3: Lobby Interface ✅</p>
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
        <p>Step 3: Lobby Interface</p>
        
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
          {!isLoggedIn ? (
            <button 
              onClick={login}
              style={{ padding: '12px 24px', fontSize: '16px', marginRight: '10px' }}
            >
              1. Login as {username}
            </button>
          ) : !connected ? (
            <button 
              onClick={connectSocket}
              style={{ padding: '12px 24px', fontSize: '16px', marginRight: '10px' }}
            >
              2. Connect to Socket.IO
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
          </ul>
          
          <div style={{ marginTop: '20px', padding: '10px', background: '#333', borderRadius: '4px' }}>
            <strong>Current Step:</strong> Step 3 - Lobby Interface<br/>
            <strong>Next:</strong> {showLobby ? 'Step 4 - Game Interface' : 'Complete authentication and connection'}
          </div>
        </div>
      </header>
    </div>
  );
}

export default App;
// DEBUG: File modified at Thu Aug  7 22:21:19 UTC 2025
