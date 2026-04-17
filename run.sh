#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="office-tracker"
ENV_FILE="$SCRIPT_DIR/.env"

# Check .env exists
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: .env file not found at $SCRIPT_DIR/.env"
  echo "Create one based on .env.example"
  exit 1
fi

# Check Docker is running; if not, try to start it via Colima
if ! docker info &>/dev/null; then
  echo "Docker not running, starting Colima..."
  colima start
  # Wait until Docker is ready
  for i in {1..10}; do
    docker info &>/dev/null && break
    sleep 2
  done
  if ! docker info &>/dev/null; then
    echo "Error: Docker still not available after starting Colima."
    exit 1
  fi
fi

# Build
echo "Building image..."
docker build -t "$IMAGE_NAME" "$SCRIPT_DIR" -q

# Run
echo ""
docker run --rm --env-file "$ENV_FILE" "$IMAGE_NAME"
