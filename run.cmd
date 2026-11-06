@echo off
setlocal
cd /d "%~dp0"
set "UDYAM_PYTHON=python"
if exist ".venv\Scripts\python.exe" set "UDYAM_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "frontend\node_modules\vite\bin\vite.js" (
  pushd frontend
  call npm.cmd ci --cache ..\.npm-cache --ignore-scripts --no-audit --no-fund
  if errorlevel 1 (
    popd
    exit /b 1
  )
  popd
)
pushd frontend
call npm.cmd run build
if errorlevel 1 (
  popd
  exit /b 1
)
popd
"%UDYAM_PYTHON%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8010 --no-access-log
exit /b %errorlevel%
