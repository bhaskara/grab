/**
 * WordInput component provides a terminal-like interface for entering words and commands.
 * Handles word input, pass/ready actions, and displays command prompt styling.
 */
import React, { useState, useRef, useEffect } from 'react';

function WordInput({ onSubmitWord, onPass, disabled, gameId, currentUsername, authToken, serverUrl, gameCreator, onAddGameEvent }) {
  const [input, setInput] = useState('');
  const [commandHistory, setCommandHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const inputRef = useRef(null);

  // Focus input on component mount and when not disabled
  useEffect(() => {
    if (!disabled && inputRef.current) {
      inputRef.current.focus();
    }
  }, [disabled]);

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    if (disabled || !input.trim()) return;

    const command = input.trim().toLowerCase();
    
    // Add to command history
    setCommandHistory(prev => [command, ...prev.slice(0, 19)]); // Keep last 20 commands
    setHistoryIndex(-1);
    
    // Handle different commands
    if (command === '!ready' || command === '!r' || command === '!pass') {
      onPass();
    } else if (command === '!end' || command === '!e') {
      handleEndGame();
    } else if (command === '!help') {
      // Help will be handled by GameLog
      if (onAddGameEvent) {
        onAddGameEvent('system', 'Commands: word (letters only), !ready/!r, !end/!e, !help');
      }
    } else if (command.match(/^[a-z]+$/)) {
      // Valid word (only lowercase letters)
      onSubmitWord(command);
    } else {
      if (onAddGameEvent) {
        onAddGameEvent('error', 'Invalid command. Use: word (letters only), !ready/!r, !end/!e, !help');
      }
    }
    
    setInput('');
  };

  // Handle keyboard navigation
  const handleKeyDown = (e) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (historyIndex < commandHistory.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setInput(commandHistory[newIndex]);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setInput(commandHistory[newIndex]);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setInput('');
      }
    } else if (e.key === 'Tab') {
      e.preventDefault();
      // Could add word completion here in the future
    }
  };

  // Handle end game command
  const handleEndGame = async () => {
    if (!authToken || !gameId) {
      console.log('Cannot end game: missing authentication or game ID');
      return;
    }

    // Check if current user is the game creator
    if (gameCreator !== currentUsername) {
      if (onAddGameEvent) {
        onAddGameEvent('error', 'Only the game creator can end the game');
      }
      console.log('Only the game creator can end the game');
      return;
    }

    if (onAddGameEvent) {
      onAddGameEvent('system', 'Ending game...');
    }

    try {
      const response = await fetch(`${serverUrl}/api/games/${gameId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to end game: ${response.status}`);
      }

      const result = await response.json();
      if (result.success && onAddGameEvent) {
        onAddGameEvent('success', 'Game ended successfully');
      } else if (onAddGameEvent) {
        onAddGameEvent('error', result.error || 'Failed to end game');
      }
    } catch (error) {
      if (onAddGameEvent) {
        onAddGameEvent('error', `Error ending game: ${error.message}`);
      }
      console.error('Error ending game:', error);
    }
  };

  const promptStyle = {
    fontFamily: 'monospace',
    fontSize: '16px',
    color: '#00ff00',
    fontWeight: 'bold',
    marginRight: '8px'
  };

  const inputStyle = {
    fontFamily: 'monospace',
    fontSize: '16px',
    backgroundColor: 'transparent',
    border: 'none',
    outline: 'none',
    color: '#fff',
    flex: 1,
    caretColor: '#00ff00'
  };

  return (
    <div className="word-input" style={{ 
      padding: '15px', 
      backgroundColor: '#111', 
      borderRadius: '8px', 
      margin: '10px 0',
      border: '1px solid #333'
    }}>
      <div style={{ marginBottom: '10px' }}>
        <h3 style={{ margin: '0 0 10px 0', color: '#fff', fontSize: '14px' }}>
          💬 Command Input
        </h3>
        <div style={{ fontSize: '12px', color: '#888', marginBottom: '15px' }}>
          Type a word to play, or use <code style={{backgroundColor: '#333', padding: '1px 4px'}}>!ready</code> to pass turn • <code style={{backgroundColor: '#333', padding: '1px 4px'}}>!help</code> for help
        </div>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', alignItems: 'center' }}>
        <span style={promptStyle}>
          {gameId ? `${gameId.toUpperCase()}` : 'GAME'}>{currentUsername ? `@${currentUsername}` : ''}&gt;
        </span>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={disabled ? "Game not active..." : "enter word, !ready, or !r"}
          style={{
            ...inputStyle,
            opacity: disabled ? 0.5 : 1,
            cursor: disabled ? 'not-allowed' : 'text'
          }}
          autoComplete="off"
          spellCheck="false"
        />
      </form>
      
      {commandHistory.length > 0 && (
        <div style={{ 
          marginTop: '10px', 
          fontSize: '11px', 
          color: '#666',
          borderTop: '1px solid #333',
          paddingTop: '8px'
        }}>
          <strong>Recent:</strong> {commandHistory.slice(0, 5).join(' • ')}
          {commandHistory.length > 5 && ' ...'}
        </div>
      )}

      <div style={{ 
        marginTop: '10px', 
        fontSize: '12px', 
        color: '#666',
        fontFamily: 'monospace'
      }}>
        <div><strong>Commands:</strong></div>
        <div>• <code>word</code> - Make a word (letters a-z only)</div>
        <div>• <code>!ready</code>, <code>!r</code>, or <code>!pass</code> - Ready for next turn</div>
        <div>• <code>!end</code> or <code>!e</code> - End the game (creator only)</div>
        <div>• <code>!help</code> - Show help information</div>
        <div>• <kbd>↑↓</kbd> - Navigate command history</div>
      </div>
    </div>
  );
}

export default WordInput;