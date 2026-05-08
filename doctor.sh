#!/usr/bin/env bash
# Ember Chat - System Doctor
# Verifies your environment is ready to run the project.
# Usage: bash doctor.sh

# Color helpers
G="\033[0;32m"; R="\033[0;31m"; Y="\033[0;33m"; B="\033[0;34m"; N="\033[0m"
ok()   { echo -e "  ${G}✓${N} $1"; }
fail() { echo -e "  ${R}✗${N} $1"; ERRORS=$((ERRORS+1)); }
warn() { echo -e "  ${Y}!${N} $1"; }
info() { echo -e "  ${B}i${N} $1"; }

ERRORS=0
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo ""
echo "============================================"
echo "  Ember Chat - System Doctor"
echo "============================================"

# 1. Required commands
echo ""
echo "[1/6] Required tools..."
for cmd in python3 node yarn; do
  if command -v $cmd >/dev/null 2>&1; then
    ok "$cmd: $($cmd --version 2>&1 | head -n1)"
  else
    fail "$cmd is NOT installed"
  fi
done

if command -v mongod >/dev/null 2>&1 || command -v docker >/dev/null 2>&1; then
  if command -v mongod >/dev/null 2>&1; then ok "mongod: $(mongod --version | head -n1)"; fi
  if command -v docker >/dev/null 2>&1; then ok "docker: $(docker --version)"; fi
else
  fail "Neither MongoDB (mongod) nor Docker is installed"
fi

# 2. Backend files
echo ""
echo "[2/6] Backend files..."
for f in backend/server.py backend/requirements.txt backend/seed_db.py backend/.env.example; do
  if [ -f "$f" ]; then ok "$f"; else fail "MISSING: $f"; fi
done
if [ -f backend/.env ]; then ok "backend/.env"; else warn "backend/.env not found - will be created from .env.example on first run"; fi

# 3. Frontend files
echo ""
echo "[3/6] Frontend files..."
for f in frontend/package.json frontend/tailwind.config.js frontend/postcss.config.js \
         frontend/public/index.html frontend/src/index.js frontend/src/index.css \
         frontend/src/App.js frontend/src/AuthContext.js frontend/src/api.js \
         frontend/src/components/AuthScreen.jsx frontend/src/components/ChatApp.jsx \
         frontend/src/components/Sidebar.jsx frontend/src/components/ChatWindow.jsx \
         frontend/src/components/CallModal.jsx frontend/src/components/FriendsModal.jsx \
         frontend/src/components/ProfileModal.jsx frontend/.env.example; do
  if [ -f "$f" ]; then ok "$f"; else fail "MISSING: $f"; fi
done
if [ -f frontend/.env ]; then ok "frontend/.env"; else warn "frontend/.env not found - will be created from .env.example on first run"; fi

# 4. Backend deps
echo ""
echo "[4/6] Backend dependencies..."
if [ -d backend/venv ]; then
  ok "backend/venv exists"
  if backend/venv/bin/python -c "import fastapi, motor, bcrypt, jwt" 2>/dev/null; then
    ok "Required Python packages installed"
  else
    fail "Python packages missing - run: cd backend && venv/bin/pip install -r requirements.txt"
  fi
else
  warn "backend/venv NOT found - run: python3 -m venv backend/venv && backend/venv/bin/pip install -r backend/requirements.txt"
fi

# 5. Frontend deps
echo ""
echo "[5/6] Frontend dependencies..."
if [ -d frontend/node_modules ]; then
  ok "frontend/node_modules exists"
  if [ -d frontend/node_modules/react ] && [ -d frontend/node_modules/react-router-dom ] && [ -d frontend/node_modules/axios ]; then
    ok "Core packages (react, react-router-dom, axios) installed"
  else
    fail "Some packages missing - run: cd frontend && yarn install"
  fi
else
  warn "frontend/node_modules NOT found - run: cd frontend && yarn install"
fi

# 6. MongoDB connectivity
echo ""
echo "[6/6] MongoDB connectivity..."
if command -v mongosh >/dev/null 2>&1; then
  if mongosh --quiet --eval "db.runCommand({ping:1})" mongodb://localhost:27017 2>/dev/null | grep -q "ok"; then
    ok "MongoDB is reachable at mongodb://localhost:27017"
  else
    warn "Cannot connect to MongoDB at mongodb://localhost:27017"
    info "Start it with:  mongod --dbpath ~/data/db"
    info "    or Docker:  docker run -d --name ember-mongo -p 27017:27017 mongo:7"
  fi
elif command -v nc >/dev/null 2>&1 && nc -z localhost 27017 2>/dev/null; then
  ok "Port 27017 is open (MongoDB likely running)"
else
  warn "Could not verify MongoDB. Make sure it's running on port 27017."
fi

# Summary
echo ""
echo "============================================"
if [ $ERRORS -eq 0 ]; then
  echo -e "  ${G}All checks passed!${N}"
  echo ""
  echo "  Next steps:"
  echo "    1. Make sure MongoDB is running"
  echo "    2. Run:  ./start.sh    (or start.bat on Windows)"
  echo "    3. Open: http://localhost:3000"
else
  echo -e "  ${R}$ERRORS issue(s) found.${N} Fix the items above and re-run this doctor."
fi
echo "============================================"
echo ""
exit $ERRORS
