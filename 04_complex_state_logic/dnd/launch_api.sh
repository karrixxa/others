#!/bin/bash
# Kill any existing processes on the required ports
fuser -k 10001/tcp 2>/dev/null
fuser -k 10002/tcp 2>/dev/null

echo "Cleaning ports 10001 and 10002..."

# Launch the C2 Builder API in the background
# Using 'uv run' to ensure the environment is correct
cd /home/cxiong/hermes_rpg/services
nohup uv run python c2_builder_api.py > api_log.txt 2>&1 &

echo "C2 Builder API launched in background on port 10002. Logs: services/api_log.txt"
