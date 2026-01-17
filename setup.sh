#!/bin/bash

echo "========================================="
echo "Voice-to-Text Tool Setup"
echo "========================================="
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew is not installed."
    echo "Please install Homebrew first: https://brew.sh"
    exit 1
fi

echo "✓ Homebrew found"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed."
    echo "Please install Python 3: brew install python"
    exit 1
fi

echo "✓ Python 3 found ($(python3 --version))"

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo "⚠️  AWS CLI is not installed."
    echo "Installing AWS CLI..."
    brew install awscli
fi

echo "✓ AWS CLI found"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials are not configured."
    echo "Please run: aws configure"
    exit 1
fi

echo "✓ AWS credentials configured"

# Install PortAudio
echo ""
echo "Installing PortAudio (required for PyAudio)..."
if ! brew list portaudio &> /dev/null; then
    brew install portaudio
    echo "✓ PortAudio installed"
else
    echo "✓ PortAudio already installed"
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "✅ Setup Complete!"
    echo "========================================="
    echo ""
    echo "To start the voice-to-text tool, run:"
    echo "  python3 voice_to_text.py"
    echo ""
    echo "Press and hold Cmd+Shift+Space to record."
    echo "Release to transcribe and paste."
    echo ""
else
    echo ""
    echo "❌ Failed to install Python dependencies."
    echo "Please check the error messages above."
    exit 1
fi
