@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
  echo.
  echo Data Coach is not set up yet.
  echo Double-click "Setup Data Coach.bat" once, then try again.
  echo.
  pause
  exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "launcher.pyw"
