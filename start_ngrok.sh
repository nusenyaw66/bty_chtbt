#!/bin/bash

# Ngrok tunnel script for Flask API on Mac
# Run this script on your Mac (10.20.11.121) to tunnel to Flask API (localhost:8888)

# Flask API configuration (running on this Mac)
LOCAL_HOST="localhost"
LOCAL_PORT="8888"

echo "========================================="
echo "Starting ngrok tunnel to Flask API"
echo "========================================="
echo "Flask API Address: $LOCAL_HOST:$LOCAL_PORT"
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "ERROR: ngrok is not installed or not in PATH"
    echo "Please install ngrok from: https://ngrok.com/download"
    echo "Or use Homebrew: brew install ngrok/ngrok/ngrok"
    exit 1
fi

# Check if Flask API is running (optional, but helpful)
echo "Checking if Flask API is running..."
if curl -s "http://$LOCAL_HOST:$LOCAL_PORT/api/health" > /dev/null 2>&1; then
    echo "✓ Flask API is reachable"
else
    echo "⚠ Warning: Flask API might not be running on port $LOCAL_PORT"
    echo "  Make sure to start it with: python qa_lms_api.py"
fi

echo ""
echo "Starting ngrok tunnel..."
echo "Public URL will be displayed below once ngrok starts"
echo ""
echo "Press Ctrl+C to stop the tunnel"
echo "========================================="
echo ""

# Start ngrok tunnel
ngrok http "$LOCAL_PORT" --log=stdout

