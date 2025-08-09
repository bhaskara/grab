/**
 * LetterPool component displays the available letters in the game pool.
 * Shows letter tiles with their counts and point values from Scrabble scoring.
 */
import React from 'react';

// Scrabble letter point values
const LETTER_POINTS = {
  'a': 1, 'b': 3, 'c': 3, 'd': 2, 'e': 1, 'f': 4, 'g': 2, 'h': 4, 'i': 1, 'j': 8,
  'k': 5, 'l': 1, 'm': 3, 'n': 1, 'o': 1, 'p': 3, 'q': 10, 'r': 1, 's': 1, 't': 1,
  'u': 1, 'v': 4, 'w': 4, 'x': 8, 'y': 4, 'z': 10
};

function LetterPool({ pool }) {
  if (!pool || !Array.isArray(pool)) {
    return (
      <div className="letter-pool" style={{ padding: '15px', backgroundColor: '#222', borderRadius: '8px', margin: '10px 0' }}>
        <h3 style={{ margin: '0 0 10px 0', color: '#fff' }}>📚 Available Letters</h3>
        <div style={{ color: '#888', fontStyle: 'italic' }}>No letters available in pool</div>
      </div>
    );
  }

  // Convert pool array [1, 0, 2, 0, 1, ...] to individual letter tiles
  const letters = [];
  pool.forEach((count, index) => {
    if (count > 0) {
      const letter = String.fromCharCode(97 + index); // 'a' + index
      const points = LETTER_POINTS[letter] || 1;
      // Create individual tiles for each copy of the letter
      for (let i = 0; i < count; i++) {
        letters.push({
          letter: letter,
          points: points
        });
      }
    }
  });

  return (
    <div className="letter-pool" style={{ padding: '15px', backgroundColor: '#222', borderRadius: '8px', margin: '10px 0' }}>
      <h3 style={{ margin: '0 0 15px 0', color: '#fff' }}>📚 Available Letters</h3>
      <div className="letters-container" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
        {letters.length === 0 ? (
          <div style={{ color: '#888', fontStyle: 'italic', width: '100%' }}>
            Pool is empty - waiting for next letter draw
          </div>
        ) : (
          letters.map(({ letter, points }, index) => (
            <div 
              key={`${letter}-${index}`} 
              className="letter-tile"
              style={{
                position: 'relative',
                backgroundColor: '#f4f1e8',
                border: '2px solid #8B4513',
                borderRadius: '6px',
                width: '45px',
                height: '45px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                fontFamily: 'monospace, serif',
                fontWeight: 'bold',
                boxShadow: '2px 2px 4px rgba(0,0,0,0.3)'
              }}
            >
              <div 
                className="letter-char" 
                style={{ 
                  fontSize: '20px', 
                  color: '#2c1810',
                  lineHeight: '1'
                }}
              >
                {letter.toUpperCase()}
              </div>
              <div 
                className="letter-points" 
                style={{ 
                  fontSize: '10px', 
                  color: '#2c1810',
                  position: 'absolute',
                  bottom: '2px',
                  right: '4px'
                }}
              >
                {points}
              </div>
            </div>
          ))
        )}
      </div>
      {letters.length > 0 && (
        <div style={{ 
          marginTop: '10px', 
          fontSize: '12px', 
          color: '#aaa',
          textAlign: 'center'
        }}>
          {new Set(letters.map(l => l.letter)).size} different letters • {letters.length} total tiles
        </div>
      )}
    </div>
  );
}

export default LetterPool;