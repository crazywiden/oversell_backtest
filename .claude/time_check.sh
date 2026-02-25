#!/bin/bash
# Read the JSON input that Claude provides
input=$(cat)
# Extract duration (requires 'jq' installed: brew install jq)
duration=$(echo "$input" | jq -r '.cost.total_api_duration_ms // 0')
# Convert to seconds
seconds=$(echo "scale=2; $duration / 1000" | bc)
echo "⏱️ ${seconds}s"