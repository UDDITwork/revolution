@echo off
echo ===================================
echo SQLite3 Workaround - Installation
echo ===================================
echo.

echo Step 1: Installing pysqlite3-binary...
echo.
pip install pysqlite3-binary
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install pysqlite3-binary
    echo Please check your pip installation and try again
    pause
    exit /b 1
)

echo.
echo ===================================
echo Step 2: Installing all dependencies...
echo ===================================
echo.
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    echo Please check requirements.txt and try again
    pause
    exit /b 1
)

echo.
echo ===================================
echo Step 3: Testing sqlite3 fix...
echo ===================================
echo.
python test_sqlite.py
if errorlevel 1 (
    echo.
    echo ERROR: SQLite3 test failed
    echo Please check the output above for errors
    pause
    exit /b 1
)

echo.
echo ===================================
echo SUCCESS!
echo ===================================
echo.
echo All tests passed! You can now run:
echo   streamlit run app.py
echo.
echo The app will have:
echo   - Full Memori conversation memory
echo   - PPTX processing with LibreOffice
echo   - Claude Sonnet 4.5 for Q&A
echo   - Persistent context across sessions
echo.
pause
