import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import './App.css';

function App() {
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');

  useEffect(() => {
    // Test Socket.IO connection to server (Step 1 requirement)
    const newSocket = io('http://localhost:5000', {
      autoConnect: false
    });

    newSocket.on('connect', () => {
      setConnected(true);
      setConnectionStatus('Connected');
      console.log('Socket.IO connected successfully');
    });

    newSocket.on('disconnect', () => {
      setConnected(false);
      setConnectionStatus('Disconnected');
      console.log('Socket.IO disconnected');
    });

    newSocket.on('error', (error) => {
      setConnectionStatus('Error: ' + error);
      console.error('Socket.IO error:', error);
    });

    setSocket(newSocket);

    return () => {
      if (newSocket) {
        newSocket.disconnect();
      }
    };
  }, []);

  const testConnection = () => {
    if (socket) {
      socket.connect();
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Grab Game - Web Frontend</h1>
        <p>Step 1: React Setup + Socket.IO</p>
        
        <div style={{ margin: '20px' }}>
          <p>Connection Status: <span style={{ color: connected ? 'green' : 'red' }}>
            {connectionStatus}
          </span></p>
          
          <button onClick={testConnection} disabled={connected}>
            Test Socket.IO Connection
          </button>
        </div>

        <div style={{ marginTop: '20px', fontSize: '14px', textAlign: 'left' }}>
          <h3>Step 1 Test Results:</h3>
          <ul>
            <li>✅ React app created and running</li>
            <li>✅ Socket.IO client library installed</li>
            <li>{socket ? '✅' : '❌'} Socket.IO client initialized</li>
            <li>{connected ? '✅' : '⏳'} Connection to server (requires server running)</li>
          </ul>
        </div>
      </header>
    </div>
  );
}

export default App;
