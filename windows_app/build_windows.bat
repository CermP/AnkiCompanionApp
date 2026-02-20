@echo off
REM Build CardsCompanion as a standalone Windows .exe
REM Requires Python 3.8+ and pip

echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Building CardsCompanion.exe...
pyinstaller --onefile --windowed --name CardsCompanion --icon=NONE cards_companion.py

echo.
echo Done! The executable is in the dist/ folder.
echo Copy dist\CardsCompanion.exe to wherever you like.
pause
