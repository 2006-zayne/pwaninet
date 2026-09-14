#!/bin/bash
# PwaniNet Cloudflare Tunnel Credential Rotation Validator
# Validates that the active token is configured and is NOT the compromised historical credential.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PWANINET_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PWANINET_DIR"

# Compromised token SHA-256 fingerprint from commit aa1ee041ffe868d239078093bbae6aa73f813aaf
COMPROMISED_SHA="1c7849e7b26c710c92bbbb5c15b9c5bf731fe4ffb233c10a484ca7fc20c3260d"

# Load environment
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
  echo "[STATUS] FAIL: CLOUDFLARE_TUNNEL_TOKEN is not set in environment or .env."
  exit 1
fi

ACTIVE_SHA=$(printf "%s" "$CLOUDFLARE_TUNNEL_TOKEN" | sha256sum | awk '{print $1}')

if [ "$ACTIVE_SHA" = "$COMPROMISED_SHA" ]; then
  echo "[STATUS] PENDING: Active token matches the compromised historical token from commit aa1ee04."
  echo "[ACTION REQUIRED] Log into Cloudflare Zero Trust dashboard, revoke tunnel, generate a new token, and update .env."
  exit 2
else
  echo "[STATUS] SUCCESS: Active token has been rotated and differs from the compromised historical credential."
  exit 0
fi
