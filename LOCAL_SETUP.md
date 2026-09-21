# Ledgerline — Run on Your Own Windows PC

This app is a normal web app (React frontend + FastAPI backend + MongoDB database).
Running it "locally" means all three pieces run on your own PC and you open it in
your browser at `http://localhost:3000` — no internet connection required once set up.

> Note: this is **not** a single double-click `.exe` installer (that would need a
> separate packaging project — Electron + bundling Python + bundling MongoDB — which
> is a bigger, dedicated build). What's below is the fastest, most reliable way to
> get the exact same app running fully offline on your PC today. Ask me if you'd
> like me to scope the full `.exe` packaging as a follow-up task.

## 1. Get the code
Use the **"Save to GitHub"** button in the Emergent chat to push this project to a
GitHub repo, then `git clone` it onto your PC. (Or download the code export if you
already have it.)

## 2. Install prerequisites (one-time)
- **Python 3.11+** — https://www.python.org/downloads/ (check "Add to PATH" during install)
- **Node.js 18+ and Yarn** — https://nodejs.org/ then run `npm install -g yarn`
- **MongoDB Community Server** — https://www.mongodb.com/try/download/community
  Install it as a Windows Service (default option) — it will run automatically at
  `mongodb://localhost:27017` in the background.

## 3. Configure environment files
**backend/.env** (create this file, copy from `backend/.env.local.example`):
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="ledgerline"
CORS_ORIGINS="*"
```

**frontend/.env** (create this file, copy from `frontend/.env.local.example`):
```
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=0
```

## 4. Install dependencies (one-time, from the project root)
```
cd backend
pip install -r requirements.txt
cd ../frontend
yarn install
```

## 5. Start the app
Easiest: double-click `start-local.bat` in the project root (Windows). It opens two
windows — one for the backend, one for the frontend — and leaves them running.

Or manually, in two separate terminals:
```
# Terminal 1 — backend
cd backend
uvicorn server:app --host 0.0.0.0 --port 8001

# Terminal 2 — frontend
cd frontend
yarn start
```

Then open **http://localhost:3000** in your browser. The app talks to your local
MongoDB — nothing leaves your PC.

## Notes
- This local database starts empty (no demo data), same as the current preview.
- To stop, close the two terminal/command windows (or press Ctrl+C in each).
- If MongoDB isn't running as a service, start it manually first with `mongod`.
