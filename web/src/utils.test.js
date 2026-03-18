/**
 * Tests for shared utility constants and functions.
 */
import { SCRABBLE_POINTS, LETTER_POINTS, calculateWordScore } from './utils';

describe('SCRABBLE_POINTS', () => {
  test('has entries for all 26 letters', () => {
    expect(Object.keys(SCRABBLE_POINTS)).toHaveLength(26);
    for (let i = 0; i < 26; i++) {
      const letter = String.fromCharCode(97 + i);
      expect(SCRABBLE_POINTS).toHaveProperty(letter);
      expect(typeof SCRABBLE_POINTS[letter]).toBe('number');
    }
  });

  test('has correct values for known letters', () => {
    expect(SCRABBLE_POINTS['a']).toBe(1);
    expect(SCRABBLE_POINTS['q']).toBe(10);
    expect(SCRABBLE_POINTS['z']).toBe(10);
    expect(SCRABBLE_POINTS['x']).toBe(8);
    expect(SCRABBLE_POINTS['k']).toBe(5);
  });

  test('LETTER_POINTS is the same object as SCRABBLE_POINTS', () => {
    expect(LETTER_POINTS).toBe(SCRABBLE_POINTS);
  });
});

describe('calculateWordScore', () => {
  test('calculates score for "hello"', () => {
    // h=4, e=1, l=1, l=1, o=1 = 8
    expect(calculateWordScore('hello')).toBe(8);
  });

  test('returns 0 for empty string', () => {
    expect(calculateWordScore('')).toBe(0);
  });

  test('is case-insensitive', () => {
    expect(calculateWordScore('HELLO')).toBe(calculateWordScore('hello'));
  });

  test('calculates score for high-value word', () => {
    // q=10, u=1, i=1, z=10 = 22
    expect(calculateWordScore('quiz')).toBe(22);
  });

  test('returns 0 for non-letter characters', () => {
    expect(calculateWordScore('123')).toBe(0);
  });
});
