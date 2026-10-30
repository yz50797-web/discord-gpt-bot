@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem 第一次執行（例如從 GitHub 下載）時沒有 .venv，自動建立並安裝套件
if not exist ".venv\Scripts\python.exe" (
    where python >nul 2>nul || (
        echo 找不到 Python，請先到 https://www.python.org/downloads/ 安裝，安裝時勾選 "Add python.exe to PATH"。
        pause
        exit /b 1
    )
    echo 第一次執行，正在建立 Python 環境並安裝套件...
    python -m venv .venv || (pause & exit /b 1)
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || (pause & exit /b 1)
)

rem 沒有 .env 就從範本複製一份，提醒填金鑰
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo 已建立 .env，請打開它填入 DISCORD_TOKEN 和 OPENAI_API_KEY 後再執行一次。
    pause
    exit /b 1
)

".venv\Scripts\python.exe" bot.py
pause