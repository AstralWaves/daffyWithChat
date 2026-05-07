@echo off
REM Ember Chat - one-command starter for Windows
setlocal

cd /d "%~dp0"

echo Ember Chat - Starting all services
echo -----------------------------------

REM 1. Backend setup
if not exist "backend\venv" (
  echo Creating Python venv...
  python -m venv backend\venv
)
echo Installing backend dependencies...
backend\venv\Scripts\pip.exe install -q -r backend\requirements.txt

if not exist "backend\.env" (
  copy backend\.env.example backend\.env >NUL
  echo Created backend\.env from template
)

REM 2. Frontend setup
if not exist "frontend\node_modules" (
  echo Installing frontend dependencies ^(may take a couple minutes^)...
  pushd frontend
  call yarn install
  popd
)

if not exist "frontend\.env" (
  copy frontend\.env.example frontend\.env >NUL
  echo Created frontend\.env from template
)

REM 3. Start backend in a new window
echo Starting backend on http://localhost:8001 ...
start "Ember Backend" cmd /k "cd backend && venv\Scripts\uvicorn.exe server:app --reload --host 0.0.0.0 --port 8001"

REM 4. Start frontend in a new window
timeout /t 3 /nobreak >NUL
echo Starting frontend on http://localhost:3000 ...
start "Ember Frontend" cmd /k "cd frontend && yarn start"

echo.
echo Both services launched in new windows.
echo Open http://localhost:3000 in your browser.
echo Make sure MongoDB is running on port 27017.
endlocal
