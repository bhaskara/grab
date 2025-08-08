/**
 * GameLog component displays a terminal-like log of game events, moves, and messages.
 * Shows move results, player connections, game status updates, and system messages.
 */
import React, { useState, useEffect, useRef } from 'react';

function GameLog({ 
  messages, 
  maxMessages = 100,
  autoScroll = true 
}) {
  const [isScrolledToBottom, setIsScrolledToBottom] = useState(true);
  const logRef = useRef(null);
  const endRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive (if user hasn't scrolled up)
  useEffect(() => {
    if (autoScroll && isScrolledToBottom && endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, autoScroll, isScrolledToBottom]);

  // Monitor scroll position to determine if user has scrolled up
  const handleScroll = () => {
    if (!logRef.current) return;
    
    const { scrollTop, scrollHeight, clientHeight } = logRef.current;
    const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10; // 10px threshold
    setIsScrolledToBottom(isAtBottom);
  };

  // Format timestamp
  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  // Get message style based on type
  const getMessageStyle = (type) => {
    const baseStyle = {
      fontFamily: 'monospace',
      fontSize: '13px',
      padding: '2px 0',
      wordWrap: 'break-word'
    };

    switch (type) {
      case 'system':
        return { ...baseStyle, color: '#00ff00' };
      case 'error':
        return { ...baseStyle, color: '#ff4444' };
      case 'success':
        return { ...baseStyle, color: '#28a745' };
      case 'move':
        return { ...baseStyle, color: '#fff' };
      case 'connection':
        return { ...baseStyle, color: '#ffa500' };
      case 'game_event':
        return { ...baseStyle, color: '#87ceeb' };
      default:
        return { ...baseStyle, color: '#ccc' };
    }
  };

  // Format message content with terminal-like prefixes
  const formatMessage = (message) => {
    const time = formatTime(message.timestamp);
    let prefix = '';
    
    switch (message.type) {
      case 'system':
        prefix = '[SYS]';
        break;
      case 'error':
        prefix = '[ERR]';
        break;
      case 'success':
        prefix = '[OK]';
        break;
      case 'move':
        prefix = '[MOVE]';
        break;
      case 'connection':
        prefix = '[CONN]';
        break;
      case 'game_event':
        prefix = '[GAME]';
        break;
      default:
        prefix = '[INFO]';
    }

    return `${time} ${prefix} ${message.text}`;
  };

  // Limit messages to prevent memory issues
  const displayMessages = messages.slice(-maxMessages);

  return (
    <div className="game-log" style={{ 
      padding: '15px', 
      backgroundColor: '#111', 
      borderRadius: '8px', 
      margin: '10px 0',
      border: '1px solid #333',
      height: '300px',
      display: 'flex',
      flexDirection: 'column'
    }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '10px',
        borderBottom: '1px solid #333',
        paddingBottom: '8px'
      }}>
        <h3 style={{ margin: 0, color: '#fff', fontSize: '14px' }}>
          📋 Game Log
        </h3>
        <div style={{ fontSize: '11px', color: '#666' }}>
          {displayMessages.length} messages
          {!isScrolledToBottom && (
            <button
              onClick={() => endRef.current?.scrollIntoView({ behavior: 'smooth' })}
              style={{
                marginLeft: '10px',
                backgroundColor: '#333',
                color: '#fff',
                border: '1px solid #555',
                borderRadius: '3px',
                padding: '2px 6px',
                fontSize: '10px',
                cursor: 'pointer'
              }}
            >
              ↓ Scroll to bottom
            </button>
          )}
        </div>
      </div>

      <div 
        ref={logRef}
        onScroll={handleScroll}
        className="log-messages"
        style={{ 
          flex: 1,
          overflowY: 'auto',
          backgroundColor: '#000',
          padding: '10px',
          borderRadius: '4px',
          border: '1px solid #333'
        }}
      >
        {displayMessages.length === 0 ? (
          <div style={{ color: '#666', fontStyle: 'italic', textAlign: 'center', padding: '20px' }}>
            Game log is empty. Start playing to see move history!
          </div>
        ) : (
          displayMessages.map((message, index) => (
            <div 
              key={`${message.timestamp}-${index}`}
              style={getMessageStyle(message.type)}
            >
              {formatMessage(message)}
            </div>
          ))
        )}
        <div ref={endRef} />
      </div>

      <div style={{ 
        marginTop: '8px', 
        fontSize: '11px', 
        color: '#666',
        textAlign: 'center'
      }}>
        Messages are displayed in real-time • Scroll up to see history
      </div>
    </div>
  );
}

export default GameLog;