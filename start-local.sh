#!/usr/bin/env bash
echo "Starting Ledgerline locally..."
echo "Make sure MongoDB is running locally (mongod) before continuing."
echo

(cd backend && uvicorn server:app --host 0.0.0.0 --port 8001) &
BACKEND_PID=$!
sleep 3
(cd frontend && yarn start) &
FRONTEND_PID=$!

echo
echo "Backend running (pid $BACKEND_PID) on http://localhost:8001"
echo "Frontend running (pid $FRONTEND_PID) on http://localhost:3000"
echo "Press Ctrl+C to stop both."
wait
