@echo off
setlocal
echo ========================================
echo   CASEBOARD SETUP - McMATH WOODS P.A.
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python 3.8+ is required but was not found in PATH.
    echo     Install it from https://www.python.org/ then rerun this script.
    pause
    exit /b 1
)

if exist ".venv" (
    echo ✓ Reusing existing .venv
) else (
    echo Creating fresh virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [!] Could not create .venv. Check permissions and try again.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat >nul 2>&1
if errorlevel 1 (
    echo [!] Failed to activate .venv. Delete the folder and retry.
    pause
    exit /b 1
)

echo Installing/updating requirements...
"%VIRTUAL_ENV%\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
"%VIRTUAL_ENV%\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [!] Dependency installation failed. Review the messages above.
    pause
    exit /b 1
)

echo.
echo ✓ Setup complete!
echo.
echo Launching Caseboard...
python run.py

if errorlevel 1 (
    echo.
    echo [!] Caseboard exited with an error. Review the output above.
)

pause
endlocal