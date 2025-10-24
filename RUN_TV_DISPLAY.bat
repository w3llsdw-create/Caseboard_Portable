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

echo Starting Caseboard TV Display...
echo.
echo Web server starting at http://127.0.0.1:8000
echo TV Display will open at http://127.0.0.1:8000/tv
echo.
echo Starting web server in background...
start /B python run_web.py

REM Wait for server to start
timeout /t 3 /nobreak >nul

echo Launching TV Display in kiosk mode...
echo.
echo Press Ctrl+C in this window to stop the server
echo Press F11 in Chrome to toggle fullscreen
echo.

REM Launch Chrome in kiosk mode (fullscreen, no UI)
start chrome --kiosk --app=http://127.0.0.1:8000/tv

REM Keep the batch file running so server stays alive
:loop
timeout /t 60 /nobreak >nul
goto loop

endlocal
