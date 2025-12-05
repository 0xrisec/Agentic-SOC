#!/bin/bash

# Agentic SOC - Quick Start Script

echo "🛡️  Agentic SOC - Quick Start"
echo "=============================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  No .env file found!"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "❗ IMPORTANT: Edit .env and add your OPENAI_API_KEY"
    echo ""
    read -p "Press Enter after you've configured .env..."
fi

# Start the application
echo ""
echo "Starting Agentic SOC..."
echo ""
python run.py
