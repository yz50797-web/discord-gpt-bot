@echo off
rem Keep this file ASCII-only: cmd on Chinese Windows (Big5) misreads UTF-8 text.
cd /d "%~dp0"

rem First run (e.g. downloaded from GitHub): create .venv and install packages
if not exist ".venv\Scripts\python.exe" (
    where python >nul 2>nul || (
        echo Python not found. Install it from https://www.python.org/downloads/
        echo and check "Add python.exe to PATH" during installation.
        pause
        exit /b 1
    )
    echo First run: creating Python environment and installing packages...
    python -m venv .venv || (pause & exit /b 1)
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || (pause & exit /b 1)
)

rem No .env yet: copy the template and ask for the keys
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo Created .env - open it, fill in DISCORD_TOKEN and OPENAI_API_KEY, then run start.bat again.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" bot.py
pause