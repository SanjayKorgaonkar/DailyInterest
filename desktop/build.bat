@echo off
setlocal
echo ================================================
echo   Ledgerline - Windows Installer Build
echo ================================================
echo.
echo IMPORTANT: run this on a SEPARATE local clone of the
echo project (not inside the Emergent preview environment).
echo It will overwrite frontend\.env with production values.
echo.
pause

cd %~dp0

echo.
echo [1/5] Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (echo Failed to install PyInstaller. & exit /b 1)

echo.
echo [2/5] Building backend executable (ledgerline-backend.exe)...
if exist resources\backend rmdir /s /q resources\backend
pyinstaller --distpath resources\backend --workpath build\pyi-work --noconfirm backend.spec
if errorlevel 1 (echo Backend build failed. & exit /b 1)

echo.
echo [3/5] Building frontend (production, pointing at local backend)...
pushd ..\frontend
echo REACT_APP_BACKEND_URL=http://127.0.0.1:8001> .env
call yarn install
call yarn build
if errorlevel 1 (echo Frontend build failed. & popd & exit /b 1)
popd
if exist resources\frontend-build rmdir /s /q resources\frontend-build
xcopy /E /I /Y ..\frontend\build resources\frontend-build

echo.
echo [4/5] Checking bundled MongoDB binary...
if not exist resources\mongodb\mongod.exe (
  echo.
  echo ERROR: resources\mongodb\mongod.exe is missing.
  echo Download the MongoDB Community Server ZIP ^(not the MSI^) for Windows from:
  echo https://www.mongodb.com/try/download/community
  echo then copy mongod.exe from its bin\ folder into desktop\resources\mongodb\
  echo and re-run this script.
  exit /b 1
)

echo.
echo [5/5] Packaging the installer with electron-builder...
call npm install
call npm run dist
if errorlevel 1 (echo Packaging failed. & exit /b 1)

echo.
echo ================================================
echo  Done! Find Ledgerline Setup.exe inside desktop\dist\
echo ================================================
pause
