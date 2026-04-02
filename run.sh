#!/bin/bash

source /home/headless/conda/etc/profile.d/conda.sh

# source activate ai_instance_manager
# OR
conda activate ai_instance_manager



cd "$(dirname "$0")"

echo "--- current dir:"
pwd


# uvicorn main:app --reload --host "0.0.0.0" --port 42014 --log-level debug

APP_LOG_LEVEL="debug" 

echo "starting uvicorn with log level: $APP_LOG_LEVEL"

uvicorn main:app --reload --host "0.0.0.0" --port 42014 --log-level $APP_LOG_LEVEL

# Ensure logs are visible: force stderr to terminal and set PYTHONUNBUFFERED
# PYTHONUNBUFFERED=1 exec uvicorn main:app --reload --host "0.0.0.0" --port 42014 --log-level debug

# For MCP server Note: 
# -c source /home/headless/conda/etc/profile.d/conda.sh && conda activate ai_instance_manager && cd /config/workspace/projects/apps/ai_instance_manager && python -m mcp.server