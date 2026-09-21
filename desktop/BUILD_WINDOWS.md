# Ledgerline — Build the Windows Installer (.exe)

This produces a real double-click installer (`Ledgerline Setup.exe`) that installs
Ledgerline as a native Windows app. When the user runs it, it silently starts its
own bundled backend and its own bundled MongoDB in the background — **no Python,
Node, or MongoDB installation is required by the end user.** Everything is
self-contained.

## Why this has to be built on Windows
Packaging tools (PyInstaller, electron-builder/NSIS) build **native, platform-specific**
binaries and don't cross-compile. A Windows `.exe` can only be produced by running
the build on an actual Windows machine (or a Windows CI runner). Everything below
has already been prepared and smoke-tested (the backend entry point + PyInstaller
spec were verified to build and run correctly) — you just need to run the final
build step once on your Windows PC.

## One-time setup on your Windows PC

1. **Get the code** — use "Save to GitHub" in the Emergent chat, then `git clone`
   it onto your Windows PC. Work from **this fresh clone**, not the live Emergent
   preview, since the build script overwrites `frontend/.env`.

2. **Install prerequisites:**
   - Python 3.11+ (https://www.python.org/downloads/, check "Add to PATH")
   - Node.js 18+ (https://nodejs.org/) then `npm install -g yarn`
   - Install the backend's Python packages once: `cd backend && pip install -r requirements.txt`

3. **Get a portable MongoDB binary** (one-time, ~100 MB):
   - Go to https://www.mongodb.com/try/download/community
   - Platform: Windows, Package: **ZIP** (not the MSI installer)
   - Extract the ZIP anywhere, then copy `bin\mongod.exe` into:
     `desktop\resources\mongodb\mongod.exe`
   - This lets the packaged app carry its own database engine — the end user never
     installs MongoDB themselves.

4. **App icon (optional):** a generated icon is already at
   `desktop\resources\icon.png`. electron-builder auto-converts it for Windows.
   If that conversion step ever fails, generate `desktop\resources\icon.ico`
   yourself (e.g. https://icoconvert.com) and change `"icon"` in
   `desktop\package.json` → `build.win.icon` to `"resources/icon.ico"`.

## Build the installer

From the `desktop/` folder, double-click **`build.bat`**. It will, in order:
1. Install PyInstaller and build `ledgerline-backend.exe` from the FastAPI backend
2. Build the React frontend pointed at the local backend (`http://127.0.0.1:8001`)
3. Verify `mongod.exe` is present
4. Run `electron-builder` to produce the final installer

Output: `desktop\dist\Ledgerline Setup.exe`

## Test the installer
Run `Ledgerline Setup.exe` on the build machine (or copy it to another Windows PC).
It installs like any normal app, adds a desktop shortcut, and on launch:
- Starts `mongod.exe` with its data folder under the app's private AppData folder
- Starts `ledgerline-backend.exe` on `127.0.0.1:8001`
- Opens the Ledgerline UI in its own window (no browser needed)

The local database starts empty, same as the current preview. Uninstalling via
Windows "Add or remove programs" removes the app; the AppData database folder is
left behind by design (so re-installing doesn't lose data) — delete
`%APPDATA%\Ledgerline` manually if you want a fully clean uninstall.

## Troubleshooting
- **"mongod.exe not found"** during build → you skipped step 3 above.
- **"Backend executable not found"** at runtime → the PyInstaller step didn't run
  before packaging; re-run `build.bat` fully.
- **Blank window on launch** → check `%APPDATA%\Ledgerline\logs` is not present
  yet (this app doesn't write logs currently); instead run the unpacked app from
  `desktop\dist\win-unpacked\Ledgerline.exe` from a terminal to see console output.
- **electron-builder fails to convert the icon** → follow the manual `.ico`
  fallback in step 4 above.
