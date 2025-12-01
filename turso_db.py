"""
Turso Database Connection Module
Provides cloud-hosted SQLite database connectivity for Render deployment.
Uses libsql-client for Turso integration.
"""

import os
import libsql_experimental as libsql

# Environment variables for Turso connection
TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")


def get_turso_connection(db_name: str = "default"):
    """
    Get a connection to the Turso database.

    Args:
        db_name: Logical database name (used for local fallback path)

    Returns:
        Connection object compatible with sqlite3 interface
    """
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        # Connect to Turso cloud database
        try:
            conn = libsql.connect(
                database=TURSO_DATABASE_URL,
                auth_token=TURSO_AUTH_TOKEN
            )
            return conn
        except Exception as e:
            print(f"⚠️ Turso connection failed: {e}")
            print("Falling back to local SQLite...")
            import sqlite3
            return sqlite3.connect(f"{db_name}.db", check_same_thread=False)
    else:
        # Fallback to local SQLite for development
        print(f"⚠️ Turso credentials not found. Using local SQLite: {db_name}.db")
        import sqlite3
        return sqlite3.connect(f"{db_name}.db", check_same_thread=False)


def is_turso_enabled() -> bool:
    """Check if Turso is properly configured."""
    return bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)


class TursoConnection:
    """
    Context manager for Turso database connections.
    Provides a consistent interface whether using Turso or local SQLite.
    """

    def __init__(self, db_name: str = "default"):
        self.db_name = db_name
        self.conn = None

    def __enter__(self):
        self.conn = get_turso_connection(self.db_name)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
        return False
