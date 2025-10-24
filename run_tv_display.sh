#!/bin/bash
# Launch Caseboard TV Display in kiosk mode

set -e

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "[!] No .venv folder found. Run setup first."
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

echo "Starting Caseboard TV Display..."
echo ""
echo "Web server starting at http://127.0.0.1:8000"
echo "TV Display will open at http://127.0.0.1:8000/tv"
echo ""

# Start web server in background
python run_web.py &
SERVER_PID=$!

# Wait for server to start
sleep 3

echo "Launching TV Display in fullscreen..."
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Try to launch Chrome in kiosk mode
if command -v google-chrome &> /dev/null; then
    google-chrome --kiosk --app=http://127.0.0.1:8000/tv &
elif command -v chromium-browser &> /dev/null; then
    chromium-browser --kiosk --app=http://127.0.0.1:8000/tv &
elif command -v chromium &> /dev/null; then
    chromium --kiosk --app=http://127.0.0.1:8000/tv &
else
    echo "Chrome/Chromium not found. Please open http://127.0.0.1:8000/tv manually"
fi

# Wait for server to exit
wait $SERVER_PID
