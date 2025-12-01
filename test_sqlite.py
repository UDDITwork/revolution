# Test script to diagnose sqlite3 issues
import sys

# Apply sqlite3 fix FIRST
import sqlite_fix

print("="*60)
print("SQLite3 Diagnostic Test")
print("="*60)
print(f"Python Version: {sys.version}")
print(f"Python Executable: {sys.executable}")
print("="*60)

try:
    import sqlite3
    print("✅ sqlite3 module found")
    print(f"   SQLite version: {sqlite3.sqlite_version}")
    print(f"   Module location: {sqlite3.__file__}")

    # Test database operations
    print("\nTesting database operations...")
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
    cursor.execute("INSERT INTO test (value) VALUES ('Hello SQLite')")
    cursor.execute("SELECT value FROM test")
    result = cursor.fetchone()
    conn.close()
    print(f"✅ SQLite operations work: {result[0]}")

except ImportError as e:
    print("❌ sqlite3 module NOT FOUND")
    print(f"   Error: {e}")
    print("\n" + "="*60)
    print("SOLUTION:")
    print("="*60)
    print("Your Python installation is missing the sqlite3 module.")
    print("\nQuickest fix:")
    print("1. Reinstall Python 3.10.11 from https://www.python.org")
    print("2. During installation, make sure ALL optional features are checked")
    print("3. Recreate your virtual environment")
    print("\nSee FIX_SQLITE3.md for detailed instructions")
    print("="*60)
    sys.exit(1)

except Exception as e:
    print(f"❌ SQLite operations failed: {e}")
    sys.exit(1)

print("\nTesting Memori...")
try:
    from memori import Memori
    print("✅ Memori can be imported successfully")
    print("   Memori is ready to use!")
except ImportError as e:
    print(f"❌ Memori import failed: {e}")
    print("\nThis is expected if sqlite3 doesn't work.")
    sys.exit(1)

print("\n" + "="*60)
print("ALL TESTS PASSED!")
print("="*60)
print("Your Python installation is ready to run the app with Memori.")
print("\nYou can now run:")
print("  streamlit run app.py")
print("="*60)
