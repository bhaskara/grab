/**
 * Shared utility constants and functions for the Grab game frontend.
 * Extracted from LetterPool.js and PlayerWords.js to avoid duplication.
 */

/**
 * Scrabble letter point values.
 * Maps each lowercase letter to its standard Scrabble tile point value.
 */
export const SCRABBLE_POINTS = {
  'a': 1, 'b': 3, 'c': 3, 'd': 2, 'e': 1, 'f': 4, 'g': 2, 'h': 4, 'i': 1, 'j': 8,
  'k': 5, 'l': 1, 'm': 3, 'n': 1, 'o': 1, 'p': 3, 'q': 10, 'r': 1, 's': 1, 't': 1,
  'u': 1, 'v': 4, 'w': 4, 'x': 8, 'y': 4, 'z': 10
};

// Alias for backward compatibility (LetterPool uses LETTER_POINTS)
export const LETTER_POINTS = SCRABBLE_POINTS;

/**
 * Calculate the Scrabble score for a word.
 *
 * Parameters
 * ----------
 * word : string
 *     The word to score. Case-insensitive.
 *
 * Returns
 * -------
 * number
 *     The sum of Scrabble point values for each letter in the word.
 *     Unknown characters contribute 0 points.
 */
export function calculateWordScore(word) {
  return word.toLowerCase().split('').reduce((sum, letter) => {
    return sum + (SCRABBLE_POINTS[letter] || 0);
  }, 0);
}
