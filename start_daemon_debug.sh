#!/bin/bash

# Start Electrum-BTX daemon with debug logging
# This will help us diagnose the connection issues

# Stop any existing daemon first
python3 ./run_electrum stop 2>/dev/null || true

# Create logs directory
mkdir -p ~/work/logs

# Start daemon with debug logging and custom data directory
echo "Starting Electrum-BTX daemon with debug logging..."
echo "Logs will be written to: ~/work/logs/"
echo "Data directory: ~/work/logs/electrum_data"

python3 ./run_electrum -v "debug,network=debug,interface=debug" -D ~/work/logs/electrum_data daemon

# If daemon starts successfully, show status
sleep 5
echo "Checking daemon status..."
python3 ./run_electrum -D ~/work/logs/electrum_data getinfo