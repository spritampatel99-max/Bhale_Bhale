@echo off
REM NovaMart - one-time local setup for Windows (safe to re-run; never deletes your data).
setlocal
cd /d "%~dp0"
echo ============================================
echo  NovaMart setup
echo ============================================

set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY ( where py >nul 2>nul && set "PY=py -3" )
if not defined PY (
  echo [ERROR] Python was not found. Install Python 3.12 or newer from https://www.python.org/downloads/
  echo         and tick "Add python.exe to PATH" during installation, then run this file again.
  pause & exit /b 1
)
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)"
if errorlevel 1 (
  echo [ERROR] Django 6 needs Python 3.12 or newer. Your version is:
  %PY% --version
  pause & exit /b 1
)

if not exist "venv\Scripts\python.exe" (
  echo [1/5] Creating virtual environment in .\venv ...
  %PY% -m venv venv
  if errorlevel 1 ( echo [ERROR] Could not create the virtual environment. & pause & exit /b 1 )
) else (
  echo [1/5] Virtual environment already exists - reusing it.
)

echo [2/5] Installing dependencies ...
"venv\Scripts\python.exe" -m pip install --upgrade pip >nul
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 ( echo [ERROR] Dependency installation failed. Check your internet connection. & pause & exit /b 1 )

echo [3/5] Applying database migrations ...
"venv\Scripts\python.exe" manage.py migrate
if errorlevel 1 ( echo [ERROR] Migration failed. & pause & exit /b 1 )

echo [4/5] Loading demo data (safe to repeat; no duplicates) ...
"venv\Scripts\python.exe" manage.py seed_demo_data --with-demo-users
if errorlevel 1 ( echo [ERROR] Seeding failed. & pause & exit /b 1 )

echo [5/5] Running system check ...
"venv\Scripts\python.exe" manage.py check

echo.
echo Setup complete. Start the website by double-clicking run_windows.bat
echo (or run: venv\Scripts\python.exe manage.py runserver)
pause
