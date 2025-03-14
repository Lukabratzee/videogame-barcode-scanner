#!/bin/bash
# This script finds and force-kills any process using port 5001

pids=$(lsof -ti :5001)
if [ -n "$pids" ]; then
    echo "Killing processes on port 5001: $pids"
    kill -9 $pids
else
    echo "No processes found on port 5001."
fi