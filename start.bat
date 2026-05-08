@echo off
REM ============================================
REM  Ember Chat - One-command starter (Windows)
REM ============================================
REM  This script will:
REM    1. Create Python venv + install backend deps
REM    2. Install frontend deps with yarn
REM    3. Create .env files from .env.example if missing
REM    4. Start MongoDB via Docker if not running
REM    5. Start backend on :8001 and frontend on :3000

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ============================================
echo   Ember Chat - Starting all services
echo ============================================
echo.

REM ------------- 1. Check prerequisites -------------
echo Checking prerequisites...
where python >nul 2>&1
if errorlevel 1 (
  echo [X] Python not found. Install from https://www.python.org/downloads/
  pause
  exit /b 1
)
where yarn >nul 2>&1
if errorlevel 1 (
  echo [X] yarn not found. Install with: npm install -g yarn
  pause
  exit /b 1
)
echo [OK] Prerequisites OK

REM ------------- 2. Backend setup -------------
echo.
echo [Backend]
if not exist "backend\venv" (
  echo   Creating Python venv...
  python -m venv backend\venv
)
echo   Installing Python dependencies...
backend\venv\Scripts\pip.exe install -q --upgrade pip
backend\venv\Scripts\pip.exe install -q -r backend\requirements.txt
echo   [OK] Backend deps ready

if not exist "backend\.env" (
  copy backend\.env.example backend\.env >nul
  echo   [!] Created backend\.env from template - review it if needed
)

REM ------------- 3. Frontend setup -------------
echo.
echo [Frontend]
if not exist "frontend\node_modules\react" (
  echo   Installing Node dependencies ^(may take 1-3 minutes^)...
  pushd frontend
  call yarn install --silent
  popd
) else (
  echo   node_modules already present, skipping yarn install
)
echo   [OK] Frontend deps ready

if not exist "frontend\.env" (
  copy frontend\.env.example frontend\.env >nul
  echo   [!] Created frontend\.env from template
)

REM ------------- 4. MongoDB -------------
echo.
echo [MongoDB]
where docker >nul 2>&1
if not errorlevel 1 (
  docker ps --format "{{.Names}}" 2>nul | findstr /R "^ember-mongo$" >nul
  if errorlevel 1 (
    echo   Starting MongoDB via Docker...
    docker rm -f ember-mongo >nul 2>&1
    docker run -d --name ember-mongo -p 27017:27017 -v ember_mongo_data:/data/db mongo:7 >nul
    echo   Waiting for MongoDB to be ready...
    timeout /t 5 /nobreak >nul
    echo   [OK] MongoDB started ^(Docker^)
  ) else (
    echo   [OK] Docker container ember-mongo already running
  )
) else (
  echo   [!] Docker not found - assuming MongoDB is running locally on :27017
  echo       If not, install MongoDB or Docker first.
)

REM ------------- 5. Start servers -------------
echo.
echo Starting services...
echo   Backend  -^> http://localhost:8001
echo   Frontend -^> http://localhost:3000
echo.
echo Two new terminal windows will open. Close them to stop the servers.
echo.

start "Ember Backend" cmd /k "cd /d %CD%\backend && venv\Scripts\uvicorn.exe server:app --reload --host 0.0.0.0 --port 8001"

timeout /t 3 /nobreak >nul

start "Ember Frontend" cmd /k "cd /d %CD%\frontend && yarn start"

echo.
echo Both services launched. Open http://localhost:3000 in your browser.
echo.
endlocal
