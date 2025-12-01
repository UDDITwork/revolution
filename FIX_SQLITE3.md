# Fixing sqlite3 Module Error for Memori

## The Problem

Your Python 3.10.11 installation is missing the `sqlite3` module, which is required by Memori. This is a common issue with certain Python installations on Windows.

## Solution Options

### Option 1: Reinstall Python 3.10 (RECOMMENDED)

1. **Download Python 3.10.11** from official source:
   - Go to: https://www.python.org/downloads/release/python-31011/
   - Download: "Windows installer (64-bit)"

2. **Uninstall current Python 3.10**:
   - Go to Settings > Apps > Apps & features
   - Find "Python 3.10.11"
   - Click Uninstall

3. **Install Python with custom options**:
   - Run the installer
   - ✅ CHECK "Add Python to PATH"
   - Click "Customize installation"
   - Make sure **ALL** optional features are checked (especially "tcl/tk and IDLE")
   - Click Next
   - In Advanced Options, check:
     - ✅ Install for all users
     - ✅ Associate files with Python
     - ✅ Create shortcuts
     - ✅ Add Python to environment variables
     - ✅ Precompile standard library
   - Install

4. **Verify installation**:
   ```cmd
   python --version
   python -c "import sqlite3; print('SQLite3 works!')"
   ```

5. **Recreate virtual environment**:
   ```cmd
   cd C:\Users\Uddit\Downloads\COOKBOOK
   rmdir /s /q venv
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

### Option 2: Copy DLL Files (QUICK FIX)

If Python 3.10.11 is installed elsewhere on your system with working sqlite3:

1. **Find working sqlite3.dll**:
   - Check: `C:\Python310\DLLs\sqlite3.dll`
   - Or search Windows for `sqlite3.dll`

2. **Copy to your Python installation**:
   ```cmd
   copy "C:\Python310\DLLs\sqlite3.dll" "C:\Users\Uddit\AppData\Local\Programs\Python\Python310\DLLs\"
   ```

3. **Test**:
   ```cmd
   C:\Users\Uddit\AppData\Local\Programs\Python\Python310\python.exe -c "import sqlite3; print('Works!')"
   ```

### Option 3: Download SQLite DLL Manually

1. **Download sqlite3.dll**:
   - Go to: https://www.sqlite.org/download.html
   - Download: "sqlite-dll-win-x64-*.zip" (64-bit Windows)
   - Extract `sqlite3.dll`

2. **Place in Python DLLs folder**:
   ```cmd
   copy sqlite3.dll "C:\Users\Uddit\AppData\Local\Programs\Python\Python310\DLLs\"
   ```

3. **Also copy to**:
   ```cmd
   copy sqlite3.dll "C:\Users\Uddit\Downloads\COOKBOOK\venv\Scripts\"
   copy sqlite3.dll "C:\Users\Uddit\Downloads\COOKBOOK\venv\Lib\site-packages\"
   ```

4. **Test**:
   ```cmd
   venv\Scripts\activate
   python -c "import sqlite3; print('SQLite3 loaded!')"
   ```

### Option 4: Use Python from Microsoft Store (ALTERNATIVE)

If reinstalling doesn't work:

1. **Uninstall current Python 3.10**

2. **Install from Microsoft Store**:
   - Open Microsoft Store
   - Search "Python 3.10"
   - Install "Python 3.10"

3. **Recreate environment**:
   ```cmd
   cd C:\Users\Uddit\Downloads\COOKBOOK
   rmdir /s /q venv
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

## After Fixing

Once sqlite3 works, test Memori:

```cmd
cd C:\Users\Uddit\Downloads\COOKBOOK
venv\Scripts\activate

# Test sqlite3
python -c "import sqlite3; print('SQLite3:', sqlite3.sqlite_version)"

# Test Memori
python -c "from memori import Memori; print('Memori works!')"

# Run the app
streamlit run app.py
```

## Verification Steps

Run this script to verify everything works:

```python
# test_sqlite.py
import sys
print(f"Python: {sys.version}")
print(f"Executable: {sys.executable}")

try:
    import sqlite3
    print(f"✅ sqlite3 module found")
    print(f"SQLite version: {sqlite3.sqlite_version}")

    # Test database creation
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
    cursor.execute("INSERT INTO test (value) VALUES ('Hello SQLite')")
    cursor.execute("SELECT value FROM test")
    result = cursor.fetchone()
    conn.close()
    print(f"✅ SQLite operations work: {result[0]}")

except ImportError as e:
    print(f"❌ sqlite3 module not found: {e}")
    print("\nYour Python installation is missing sqlite3.")
    print("Follow Option 1 (Reinstall Python) from FIX_SQLITE3.md")

try:
    from memori import Memori
    print("✅ Memori can be imported")
except ImportError as e:
    print(f"❌ Memori import failed: {e}")
```

Save this as `test_sqlite.py` and run:
```cmd
venv\Scripts\activate
python test_sqlite.py
```

## Why This Happens

- Some Python installers (especially custom builds) don't include sqlite3
- The sqlite3 module requires `sqlite3.dll` which may be missing
- Microsoft Store Python and official Python.org installers usually include it
- Portable/embedded Python distributions often exclude it

## Recommended: Option 1

**Reinstalling Python** is the cleanest solution and prevents future issues with other modules that depend on compiled extensions.

## Need Help?

If none of these work:
1. Run `test_sqlite.py` and share the output
2. Check which Python installation you have:
   ```cmd
   where python
   python --version
   ```
3. Look for any error messages during venv creation
