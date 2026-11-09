@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul || (echo Python 3 (64-bit) is not installed. Get it from https://www.python.org/downloads/ and tick "Add python.exe to PATH". & pause & exit /b 1)
if not exist ".venv\Scripts\python.exe" (
    echo Setting up environment ^(first run only^)...
    py -3 -m venv .venv || (echo Could not create virtual environment. & pause & exit /b 1)
)
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt pyinstaller || (pause & exit /b 1)
echo Building PossibleMacroMaker.exe ...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name PossibleMacroMaker ^
    --icon assets\icon.ico ^
    --add-data "assets;assets" ^
    --add-data "app\native\pmm_runtime.dll;app\native" ^
    main.py || (echo Build failed. & pause & exit /b 1)
echo.
echo Done! Your app is in:  dist\PossibleMacroMaker\PossibleMacroMaker.exe
echo (Copy the whole dist\PossibleMacroMaker folder wherever you like.)
pause
