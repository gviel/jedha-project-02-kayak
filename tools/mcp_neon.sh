#!/bin/bash
ENV_FILE="$(dirname "$0")/../.env"
NEON_API_KEY=$(grep "^NEON_API_KEY=" "$ENV_FILE" | cut -d'=' -f2-)
exec npx -y @neondatabase/mcp-server-neon start "$NEON_API_KEY"
