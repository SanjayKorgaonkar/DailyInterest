@echo off
echo Starting Ledgerline locally...
echo Make sure MongoDB is running (as a Windows Service or via "mongod").
echo.

start "Ledgerline Backend" cmd /k "cd backend && uvicorn server:app --host 0.0.0.0 --port 8001"
timeout /t 3 /nobreak >nul
start "Ledgerline Frontend" cmd /k "cd frontend && yarn start"

echo.
echo Backend starting on http://localhost:8001
echo Frontend starting on http://localhost:3000
echo Open http://localhost:3000 in your browser once both windows show "ready".
pause
