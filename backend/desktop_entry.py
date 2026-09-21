"""
Standalone entry point used to build the Windows desktop backend executable
(ledgerline-backend.exe) via PyInstaller. The Electron shell (desktop/main.js)
spawns this executable and passes MONGO_URL / DB_NAME / CORS_ORIGINS / PORT
as environment variables before starting it - no .env file is required at
runtime because those variables are already present in the process
environment by the time `server.py` reads them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from server import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run(app, host="127.0.0.1", port=port)
