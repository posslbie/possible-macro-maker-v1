@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul || (echo Python 3 (64-bit) is not installed. Get it from https://www.python.org/downloads/ and tick "Add python.exe to PATH". & pause & exit /b 1)
if not exist ".venv\Scripts\python.exe" (
    echo Setting up environment ^(first run only^)...
    py -3 -m venv .venv || (echo Could not create virtual environment. & pause & exit /b 1)
)
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt || (pause & exit /b 1)
".venv\Scripts\python.exe" main.py
