# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a web-based implementation of "Grab" - a word game played with Scrabble tiles. The game uses an authoritative server model where clients connect via WebSocket to a Flask server that maintains all game state in-memory.

## Requirements

@doc/requirements.md

## Architecture

@doc/architecture.md

## Project Status

Currently in prototype phase - not designed for large scale deployment. Focus is on core gameplay mechanics and real-time communication patterns.

## Style guidelines

This project is for learning, so please document things.  It doesn't have to be overly verbose, but brief explanations of things will be helpful:
- Each directory should have a README.md explaining what's in this directory.
- Each file should have a comment at the top explaining what it contains.
- Each class, function, method, and test should have a docstring.  For public methods/functions, the docstring should be in Numpy style, with
  documentation of parameters and return values.  When editing functions or methods, also update their docstrings to conform to this style
  if necessary.
  
In general, things should fail early and informatively.  For example, don't silently catch exceptions and return None within library functions.  Instead, pass those exceptions up unless they can be handled (but do document this behavior).

The full test suite (pytest in the repo root) should always be run and validated to pass before making a commit.
