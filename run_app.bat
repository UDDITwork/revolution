@echo off
echo ===================================
echo Multimodal RAG with Memori
echo ===================================
echo.

REM Find the correct Python (not LibreOffice's)
set PYTHON_EXE=python

REM Check if we can find Python 3.10 specifically
if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe" (
    set "PYTHON_EXE=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe"
    echo Found Python 3.10: %PYTHON_EXE%
) else if exist "C:\Python310\python.exe" (
    set "PYTHON_EXE=C:\Python310\python.exe"
    echo Found Python 3.10: %PYTHON_EXE%
) else (
    echo Using default Python in PATH
)

echo.
echo Testing Python and sqlite3...
"%PYTHON_EXE%" sqlite_fix.py
if errorlevel 1 (
    echo.
    echo WARNING: sqlite3 test had issues, but continuing...
    echo.
)

echo.
echo Installing dependencies...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ===================================
echo Starting Streamlit App...
echo ===================================
echo.
"%PYTHON_EXE%" -m streamlit run app.py
