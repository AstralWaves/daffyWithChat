#!/usr/bin/env bash
# Ember Chat - one-command starter for Linux/Mac
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "Ember Chat - Starting all services"
echo "------------------------------------"

# 1. Backend setup
if [ ! -d "backend/venv" ]; then
  echo "Creating Python venv..."
  python3 -m venv backend/venv
fi
echo "Installing backend dependencies..."
backend/venv/bin/pip install -q -r backend/requirements.txt

if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "Created backend/.env from template"
fi

# 2. Frontend setup
if [ ! -d "frontend/node_modules" ]; then
  echo "Installing frontend dependencies (this may take a couple minutes)..."
  (cd frontend && yarn install)
fi

if [ ! -f frontend/.env ]; then
  cp frontend/.env.example frontend/.env
  echo "Created frontend/.env from template"
fi

# 3. Check MongoDB
if ! command -v mongod >/dev/null 2>&1; then
  if command -v docker >/dev/null 2>&1; then
    if ! docker ps --format '{{.Names}}' | grep -q '^ember-mongo$'; then
      echo "Starting MongoDB via Docker..."
      docker rm -f ember-mongo >/dev/null 2>&1 || true
      docker run -d --name ember-mongo -p 27017:27017 mongo:7 >/dev/null
      sleep 4
    fi
  else
    echo "WARN: MongoDB and Docker both not found. Install one before continuing."
  fi
fi

# 4. Start backend in background
echo "Starting backend on http://localhost:8001 ..."
(cd backend && venv/bin/uvicorn server:app --reload --host 0.0.0.0 --port 8001) &
BACKEND_PID=$!

trap "echo 'Stopping...'; kill $BACKEND_PID 2>/dev/null; exit 0" INT TERM

# 5. Start frontend (foreground)
echo "Starting frontend on http://localhost:3000 ..."
sleep 2
(cd frontend && yarn start)

kill $BACKEND_PID 2>/dev/null || true
