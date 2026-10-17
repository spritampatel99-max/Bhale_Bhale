@echo off
REM NovaMart - start the development server (Windows).
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo [ERROR] The virtual environment is missing. Run setup_windows.bat first.
  pause & exit /b 1
)
"venv\Scripts\python.exe" -c "import django" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Django is not installed in the virtual environment. Run setup_windows.bat first.
  pause & exit /b 1
)
if not exist "novamart.sqlite3" (
  echo Database not found - creating it and loading demo data ...
  "venv\Scripts\python.exe" manage.py migrate
  "venv\Scripts\python.exe" manage.py seed_demo_data --with-demo-users
) else (
  "venv\Scripts\python.exe" manage.py migrate --noinput >nul
)
echo.
echo  Store:      http://127.0.0.1:8000/
echo  Dashboard:  http://127.0.0.1:8000/dashboard/
echo  Django admin: http://127.0.0.1:8000/admin/
echo  Press CTRL+C to stop the server.
echo.
"venv\Scripts\python.exe" manage.py runserver
pause
