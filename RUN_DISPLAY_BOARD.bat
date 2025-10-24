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

echo Starting Caseboard Display Board...
python run_display.py

if errorlevel 1 (
	echo.
	echo [!] Display Board exited with an error. Check the log above.
	pause
	exit /b %errorlevel%
)

endlocal
