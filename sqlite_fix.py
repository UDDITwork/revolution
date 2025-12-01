"""
SQLite3 Compatibility Fix for Windows

This module attempts to make sqlite3 available by downloading the DLL if needed.

Usage: Import this module BEFORE importing any other modules that use sqlite3
"""

import sys
import os

# Try to import the built-in sqlite3 module
try:
    import sqlite3
    print("✅ Built-in sqlite3 module is available")
except ModuleNotFoundError:
    print("⚠️  Built-in sqlite3 module not found")
    print("⚠️  Attempting to download and configure SQLite DLL...")

    try:
        import urllib.request
        import zipfile
        import shutil

        # Determine DLL directory
        if hasattr(sys, 'base_prefix'):
            dll_dir = os.path.join(sys.base_prefix, 'DLLs')
        else:
            dll_dir = os.path.join(sys.prefix, 'DLLs')

        # Create DLLs directory if it doesn't exist
        os.makedirs(dll_dir, exist_ok=True)

        sqlite_dll = os.path.join(dll_dir, 'sqlite3.dll')

        # Check if we need to download
        if not os.path.exists(sqlite_dll):
            print(f"   Downloading SQLite DLL to {dll_dir}...")

            # Download SQLite DLL for Windows (64-bit)
            url = "https://www.sqlite.org/2024/sqlite-dll-win-x64-3450100.zip"
            zip_path = os.path.join(dll_dir, 'sqlite.zip')

            try:
                urllib.request.urlretrieve(url, zip_path)

                # Extract the DLL
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(dll_dir)

                # Clean up zip file
                os.remove(zip_path)

                print(f"   ✅ SQLite DLL downloaded successfully")
            except Exception as download_error:
                print(f"   ⚠️  Failed to download DLL: {download_error}")
                print("   You may need to download manually from https://www.sqlite.org/download.html")

        # Try importing again
        import sqlite3
        print("✅ Successfully loaded sqlite3 module with downloaded DLL")

    except Exception as e:
        print(f"❌ Failed to configure sqlite3: {e}")
        print("\n" + "="*60)
        print("MANUAL FIX REQUIRED:")
        print("="*60)
        print("1. Download SQLite DLL from: https://www.sqlite.org/download.html")
        print("   - Look for 'sqlite-dll-win-x64-*.zip'")
        print("2. Extract sqlite3.dll")
        print(f"3. Copy to: {dll_dir}")
        print("="*60)
        # Don't raise - let the app try to continue
        pass

# Export sqlite3 for convenience
try:
    import sqlite3
    __all__ = ['sqlite3']
except:
    pass
