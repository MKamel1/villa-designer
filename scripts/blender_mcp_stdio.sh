#!/bin/sh
# Official Blender Lab MCP, isolated 5.2 evaluation. No TCP MCP transport.
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
evaluation_root="$project_root/out/blender52"
export BLENDER_PATH=/home/omar/opt/blender-5.2.2-linux-x64/blender
export BLENDER_USER_CONFIG="$evaluation_root/mcp-user/config"
export BLENDER_USER_SCRIPTS="$evaluation_root/mcp-user/scripts"
export BLENDER_MCP_HOST=127.0.0.1
export BLENDER_MCP_PORT=9877
exec "$evaluation_root/mcp-venv/bin/blender-mcp" --transport stdio
