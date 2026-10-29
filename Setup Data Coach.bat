@echo off
setlocal
title Data Coach Setup
cd /d "%~dp0"

set "PY=py -3"
where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul
  if errorlevel 1 (
    echo.
    echo Python 3.10 or newer was not found.
    echo Install it from https://www.python.org/downloads/ and tick
    echo "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
  )
  set "PY=python"
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating the local environment...
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
)

echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip --disable-pip-version-check

echo.
echo Installing Data Coach dependencies. This can take a few minutes...
".venv\Scripts\python.exe" -m pip install -r requirements.txt --disable-pip-version-check
if errorlevel 1 goto :fail

echo.
echo ============================================
echo  Setup complete.
echo  Double-click "Start Data Coach.bat".
echo ============================================
echo.
pause
exit /b 0

:fail
echo.
echo Setup failed. Check your internet connection, then run this file again.
echo.
pause
exit /b 1
