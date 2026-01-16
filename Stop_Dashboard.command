#!/bin/bash

# Stop the Stock Dashboard server
PID_FILE="/Users/rishiramaratnam/Documents/Project Management/.dashboard.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        kill "$PID"
        rm "$PID_FILE"
        echo "Stock Dashboard stopped."
    else
        rm "$PID_FILE"
        echo "Dashboard was not running."
    fi
else
    echo "Dashboard was not running."
fi

# Also kill any orphaned processes on port 8050
lsof -ti:8050 | xargs kill -9 2>/dev/null

sleep 2
