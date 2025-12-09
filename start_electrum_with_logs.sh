#!/bin/bash

# Start Electrum-BTX with comprehensive logging
# This will create detailed logs for debugging connection issues

# Stop any existing daemon
python3 ./run_electrum -D ~/work/logs stop 2>/dev/null || true

# Create logs directory
mkdir -p ~/.electrum/logs
mkdir -p ~/work/logs

# Set environment variables for debugging
export ELECTRUM_LOGGING_LEVEL="debug"
export PYTHONASYNCIODEBUG=1

# Start daemon with full debugging
echo "Starting Electrum-BTX with comprehensive logging..."
echo "Logs will be in ~/.electrum/logs/ and ~/work/logs/"
echo ""

# Start with network and interface debug logging
python3 ./run_electrum -v "debug,network=debug,interface=debug,ssl=debug" -D ~/work/logs daemon 2>&1 | tee ~/work/logs/daemon_startup.log &

# Store PID
DAEMON_PID=$!
echo "Daemon PID: $DAEMON_PID"

# Wait a bit for startup
sleep 5

# Check status
echo ""
echo "Checking daemon status..."
python3 ./run_electrum -D ~/work/logs getinfo

# Show log locations
echo ""
echo "Log files created:"
find ~/.electrum/logs/ -name "*.log" 2>/dev/null || echo "No logs in ~/.electrum/logs/"
find ~/work/logs/ -name "*.log" 2>/dev/null || echo "No logs in ~/work/logs/"

echo ""
echo "To follow logs in real-time:"
echo "tail -f ~/.electrum/logs/*.log"
echo "tail -f ~/work/logs/daemon_startup.log"