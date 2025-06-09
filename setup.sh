#!/bin/bash
# Setup script for Grab game development environment

echo "Setting up Grab game development environment..."

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

echo "Setup complete! To start development:"
echo "1. source venv/bin/activate"
echo "2. python run.py"