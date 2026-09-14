#!/bin/bash
# Terminal 3: Secure Global Uplink

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load virtual environment if present
if [ -f ../venv/bin/activate ]; then
  source ../venv/bin/activate
elif [ -f venv/bin/activate ]; then
  source venv/bin/activate
fi
# Load environment variables if .env exists
if [ -f .env ]; then
  set -a
  source .env
  set +a
elif [ -f ../.env ]; then
  set -a
  source ../.env
  set +a
fi

if [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
  echo "[ERROR] CLOUDFLARE_TUNNEL_TOKEN is not set. Please define it in your .env file or environment."
  exit 1
fi

# Run cloudflared with token, forwarding any optional arguments
cloudflared tunnel run --token "$CLOUDFLARE_TUNNEL_TOKEN" "$@"




