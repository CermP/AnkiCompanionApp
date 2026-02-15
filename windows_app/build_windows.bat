@echo off
REM Build AnkiCompanion as a standalone Windows .exe
REM Requires Python 3.8+ and pip

echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Building AnkiCompanion.exe...
pyinstaller --onefile --windowed --name AnkiCompanion --icon=NONE anki_companion.py

echo.
echo Done! The executable is in the dist/ folder.
echo Copy dist\AnkiCompanion.exe to wherever you like.
pause
