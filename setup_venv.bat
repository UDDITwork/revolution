@echo off
REM Setup script to create venv without LibreOffice interference

echo ===================================
echo Creating Python Virtual Environment
echo ===================================

REM Temporarily remove LibreOffice from PATH
set "ORIGINAL_PATH=%PATH%"
set "PATH=%PATH:C:\Program Files\LibreOffice\program;=%"

echo Cleaned PATH (LibreOffice removed temporarily)

REM Find Python installations (excluding LibreOffice)
echo.
echo Looking for Python installations...
where python 2>nul
if errorlevel 1 (
    echo ERROR: No Python found in PATH after removing LibreOffice
    echo.
    echo Please install Python 3.10 or 3.11 from python.org
    pause
    exit /b 1
)

REM Test sqlite3 availability
echo.
echo Testing sqlite3 module...
python -c "import sqlite3; print('SQLite version:', sqlite3.sqlite_version)" 2>nul
if errorlevel 1 (
    echo ERROR: Python found but sqlite3 module is missing!
    echo Please reinstall Python from python.org with all features enabled
    pause
    exit /b 1
)

echo SQLite3 is available!

REM Delete old venv if exists
if exist venv (
    echo.
    echo Removing old venv directory...
    rmdir /s /q venv
)

REM Create new venv
echo.
echo Creating new virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo.
echo ===================================
echo Virtual environment created successfully!
echo ===================================
echo.
echo Next steps:
echo   1. Run: venv\Scripts\activate
echo   2. Run: pip install -r requirements.txt
echo   3. Run: python test_sqlite.py
echo   4. Run: streamlit run app.py
echo.

REM Restore original PATH
set "PATH=%ORIGINAL_PATH%"
