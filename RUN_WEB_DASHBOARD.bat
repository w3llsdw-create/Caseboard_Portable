@echo off
setlocal

if not exist ".venv" (
	echo [!] No .venv folder found. Run SETUP_AND_RUN.bat first.
	pause
	exit /b 1
)

call .venv\Scripts\activate.bat >nul 2>&1
if errorlevel 1 (
	echo [!] Failed to activate .venv. Run SETUP_AND_RUN.bat to rebuild it.
	pause
	exit /b 1
)

echo Starting Caseboard Web Dashboard...
echo Web interface will be available at http://127.0.0.1:8000
echo.
python run_web.py

if errorlevel 1 (
	echo.
	echo [!] Web Dashboard exited with an error. Check the log above.
	pause
	exit /b %errorlevel%
)

endlocal
