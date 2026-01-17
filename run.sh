#!/bin/bash

# Voice-to-Text Tool Launcher
cd "$(dirname "$0")"

echo "========================================="
echo "Voice-to-Text Tool Starting..."
echo "========================================="
echo ""

# Activate virtual environment
source venv/bin/activate

# Run the application
python voice_to_text.py
