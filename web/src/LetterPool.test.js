/**
 * Tests for the LetterPool component.
 * Verifies rendering of letter tiles, point values, and edge cases.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import LetterPool from './LetterPool';

describe('LetterPool', () => {
  test('renders "Available Letters" heading', () => {
    render(<LetterPool pool={[]} />);
    expect(screen.getByText(/Available Letters/)).toBeInTheDocument();
  });

  test('shows "No letters available" when pool is null', () => {
    render(<LetterPool pool={null} />);
    expect(screen.getByText(/No letters available/)).toBeInTheDocument();
  });

  test('shows "No letters available" when pool is undefined', () => {
    render(<LetterPool />);
    expect(screen.getByText(/No letters available/)).toBeInTheDocument();
  });

  test('shows "Pool is empty" when all counts are zero', () => {
    const emptyPool = new Array(26).fill(0);
    render(<LetterPool pool={emptyPool} />);
    expect(screen.getByText(/Pool is empty/)).toBeInTheDocument();
  });

  test('renders correct number of tiles for a pool array', () => {
    // a=1, c=2 => 3 tiles total
    const pool = [1, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    render(<LetterPool pool={pool} />);
    const tiles = document.querySelectorAll('.letter-tile');
    expect(tiles).toHaveLength(3);
  });

  test('renders correct uppercase letter on tile', () => {
    // a=1 only
    const pool = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    render(<LetterPool pool={pool} />);
    expect(screen.getByText('A')).toBeInTheDocument();
  });

  test('renders point value on tile', () => {
    // q=1 (index 16, points=10)
    const pool = new Array(26).fill(0);
    pool[16] = 1; // q
    render(<LetterPool pool={pool} />);
    expect(screen.getByText('Q')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  test('renders multiple copies of the same letter', () => {
    // a=2
    const pool = [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    render(<LetterPool pool={pool} />);
    const tiles = document.querySelectorAll('.letter-tile');
    expect(tiles).toHaveLength(2);
    // Both should show 'A'
    const letterChars = document.querySelectorAll('.letter-char');
    letterChars.forEach(el => {
      expect(el.textContent).toBe('A');
    });
  });

  test('renders mixed letters in alphabetical order', () => {
    // a=1, e=1, z=1
    const pool = new Array(26).fill(0);
    pool[0] = 1;  // a
    pool[4] = 1;  // e
    pool[25] = 1; // z
    render(<LetterPool pool={pool} />);
    const letterChars = document.querySelectorAll('.letter-char');
    expect(letterChars).toHaveLength(3);
    expect(letterChars[0].textContent).toBe('A');
    expect(letterChars[1].textContent).toBe('E');
    expect(letterChars[2].textContent).toBe('Z');
  });
});
