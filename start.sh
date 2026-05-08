#!/usr/bin/env bash
# ============================================
# Ember Chat - One-command starter (Linux/Mac)
# ============================================
# This script will:
#   1. Create Python venv + install backend deps
#   2. Install frontend deps with yarn
#   3. Create .env files from .env.example if missing
#   4. Start MongoDB via Docker if not running
#   5. Start backend on :8001 and frontend on :3000

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

G="\033[0;32m"; R="\033[0;31m"; Y="\033[0;33m"; B="\033[0;34m"; N="\033[0m"
echo -e "${B}"
echo "============================================"
echo "  Ember Chat - Starting all services"
echo "============================================"
echo -e "${N}"

# ------------- 1. Check prerequisites -------------
echo "Checking prerequisites..."
MISSING=0
for cmd in python3 yarn; do
  if ! command -v $cmd >/dev/null 2>&1; then
    echo -e "${R}✗ $cmd not found${N}"
    MISSING=1
  fi
done
if [ $MISSING -eq 1 ]; then
  echo -e "${R}Please install Python 3.10+ and Yarn before continuing.${N}"
  echo "  Python: https://www.python.org/downloads/"
  echo "  Yarn:   npm install -g yarn"
  exit 1
fi
echo -e "${G}✓ Prerequisites OK${N}"

# ------------- 2. Backend setup -------------
echo ""
echo "[Backend]"
if [ ! -d "backend/venv" ]; then
  echo "  Creating Python venv..."
  python3 -m venv backend/venv
fi
echo "  Installing Python dependencies..."
backend/venv/bin/pip install -q --upgrade pip
backend/venv/bin/pip install -q -r backend/requirements.txt
echo -e "  ${G}✓ Backend deps ready${N}"

if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo -e "  ${Y}! Created backend/.env from template — review it if needed${N}"
fi

# ------------- 3. Frontend setup -------------
echo ""
echo "[Frontend]"
if [ ! -d "frontend/node_modules" ] || [ ! -d "frontend/node_modules/react" ]; then
  echo "  Installing Node dependencies (this may take 1-3 minutes)..."
  (cd frontend && yarn install --silent)
else
  echo "  node_modules already present, skipping yarn install"
fi
echo -e "  ${G}✓ Frontend deps ready${N}"

if [ ! -f frontend/.env ]; then
  cp frontend/.env.example frontend/.env
  echo -e "  ${Y}! Created frontend/.env from template${N}"
fi

# ------------- 4. MongoDB -------------
echo ""
echo "[MongoDB]"
if command -v mongosh >/dev/null 2>&1 && mongosh --quiet --eval "db.runCommand({ping:1})" mongodb://localhost:27017 2>/dev/null | grep -q "ok"; then
  echo -e "  ${G}✓ MongoDB already running on :27017${N}"
elif command -v nc >/dev/null 2>&1 && nc -z localhost 27017 2>/dev/null; then
  echo -e "  ${G}✓ Port 27017 open (MongoDB running)${N}"
elif command -v docker >/dev/null 2>&1; then
  if docker ps --format '{{.Names}}' | grep -q '^ember-mongo$'; then
    echo -e "  ${G}✓ Docker container ember-mongo already running${N}"
  else
    echo "  Starting MongoDB via Docker..."
    docker rm -f ember-mongo >/dev/null 2>&1 || true
    docker run -d --name ember-mongo -p 27017:27017 -v ember_mongo_data:/data/db mongo:7 >/dev/null
    echo "  Waiting for MongoDB to accept connections..."
    sleep 5
    echo -e "  ${G}✓ MongoDB started (Docker)${N}"
  fi
else
  echo -e "  ${R}✗ MongoDB is NOT running and Docker is not installed.${N}"
  echo "  Please install MongoDB or Docker:"
  echo "    MongoDB: https://www.mongodb.com/try/download/community"
  echo "    Docker:  https://www.docker.com/get-started"
  exit 1
fi

# ------------- 5. Start servers -------------
echo ""
echo -e "${B}Starting services...${N}"
echo "  Backend  -> http://localhost:8001"
echo "  Frontend -> http://localhost:3000"
echo ""
echo -e "${Y}Press Ctrl+C to stop everything.${N}"
echo ""

cleanup() {
  echo ""
  echo "Stopping..."
  kill $BACKEND_PID 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM

# Backend in background
(cd backend && venv/bin/uvicorn server:app --reload --host 0.0.0.0 --port 8001) &
BACKEND_PID=$!
sleep 3

# Frontend in foreground
(cd frontend && yarn start)

cleanup
