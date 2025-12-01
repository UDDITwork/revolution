@echo off
echo ===================================
echo Checking Python installations and sqlite3
echo ===================================

REM Check default Python (likely LibreOffice's)
echo.
echo 1. Default Python in PATH:
python --version
python -c "import sys; print('   Location:', sys.executable)"
python -c "import sqlite3; print('   SQLite:', sqlite3.sqlite_version)" 2>nul
if errorlevel 1 (
    echo    SQLite: NOT AVAILABLE
) else (
    echo    SQLite: AVAILABLE!
)

echo.
echo 2. Looking for other Python installations...
echo.

REM Check common Python installation locations
if exist "C:\Python310\python.exe" (
    echo Found: C:\Python310\python.exe
    "C:\Python310\python.exe" --version
    "C:\Python310\python.exe" -c "import sqlite3; print('   SQLite:', sqlite3.sqlite_version)" 2>nul || echo    SQLite: NOT AVAILABLE
    echo.
)

if exist "C:\Python311\python.exe" (
    echo Found: C:\Python311\python.exe
    "C:\Python311\python.exe" --version
    "C:\Python311\python.exe" -c "import sqlite3; print('   SQLite:', sqlite3.sqlite_version)" 2>nul || echo    SQLite: NOT AVAILABLE
    echo.
)

if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe" (
    echo Found: C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe
    "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe" --version
    "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe" -c "import sqlite3; print('   SQLite:', sqlite3.sqlite_version)" 2>nul || echo    SQLite: NOT AVAILABLE
    echo.
)

if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe" (
    echo Found: C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe
    "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe" --version
    "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe" -c "import sqlite3; print('   SQLite:', sqlite3.sqlite_version)" 2>nul || echo    SQLite: NOT AVAILABLE
    echo.
)

echo ===================================
echo.
echo RECOMMENDATION:
echo If the default Python (LibreOffice's Python 3.11.14) has SQLite,
echo we can use it directly without creating a venv!
echo.
echo LibreOffice will still work for PPTX conversion.
echo.
pause
