"""
Database module for storing finalized background sections with paragraph numbering.
"""
import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional
import re

class BackgroundDatabase:
    """SQLite database for storing finalized background sections."""

    def __init__(self, db_path="background_sections.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        """Create necessary tables for background storage."""
        cursor = self.conn.cursor()

        # Table for background sections
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS background_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                query TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table for paragraphs within each background section
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS background_paragraphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                background_id INTEGER,
                paragraph_number TEXT,
                paragraph_text TEXT,
                FOREIGN KEY (background_id) REFERENCES background_sections(id)
            )
        """)

        self.conn.commit()

    def parse_and_number_paragraphs(self, background_text: str) -> List[Tuple[str, str]]:
        """
        Parse background text and add paragraph numbers in format [1], [2], [3], etc.

        Args:
            background_text: The generated background text

        Returns:
            List of tuples (paragraph_number, paragraph_text)
        """
        # Split by double newlines or paragraph breaks
        paragraphs = [p.strip() for p in background_text.split('\n\n') if p.strip()]

        # If no double newlines, try single newlines
        if len(paragraphs) <= 1:
            paragraphs = [p.strip() for p in background_text.split('\n') if p.strip() and len(p.strip()) > 50]

        numbered_paragraphs = []
        for idx, para in enumerate(paragraphs, start=1):
            # Skip if paragraph is too short (likely a heading)
            if len(para) < 30:
                continue

            para_number = f"[{idx}]"
            numbered_paragraphs.append((para_number, para))

        return numbered_paragraphs

    def save_background(self, title: str, query: str, background_text: str) -> int:
        """
        Save a finalized background section with paragraph numbering.

        Args:
            title: Title of the invention or background section
            query: Original query used to generate the background
            background_text: Generated background text

        Returns:
            background_id: ID of the saved background section
        """
        cursor = self.conn.cursor()

        # Insert background section
        cursor.execute("""
            INSERT INTO background_sections (title, query, created_at)
            VALUES (?, ?, ?)
        """, (title, query, datetime.now()))

        background_id = cursor.lastrowid

        # Parse and number paragraphs
        numbered_paragraphs = self.parse_and_number_paragraphs(background_text)

        # Insert paragraphs
        for para_number, para_text in numbered_paragraphs:
            cursor.execute("""
                INSERT INTO background_paragraphs (background_id, paragraph_number, paragraph_text)
                VALUES (?, ?, ?)
            """, (background_id, para_number, para_text))

        self.conn.commit()
        return background_id

    def get_all_backgrounds(self) -> List[dict]:
        """
        Retrieve all saved background sections.

        Returns:
            List of dictionaries containing background details
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT id, title, query, created_at
            FROM background_sections
            ORDER BY created_at DESC
        """)

        backgrounds = []
        for row in cursor.fetchall():
            bg_id, title, query, created_at = row

            # Get paragraphs for this background
            cursor.execute("""
                SELECT paragraph_number, paragraph_text
                FROM background_paragraphs
                WHERE background_id = ?
                ORDER BY id
            """, (bg_id,))

            paragraphs = cursor.fetchall()

            backgrounds.append({
                'id': bg_id,
                'title': title,
                'query': query,
                'created_at': created_at,
                'paragraphs': paragraphs
            })

        return backgrounds

    def get_background_by_id(self, background_id: int) -> Optional[dict]:
        """
        Retrieve a specific background section by ID.

        Args:
            background_id: ID of the background section

        Returns:
            Dictionary containing background details or None
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT id, title, query, created_at
            FROM background_sections
            WHERE id = ?
        """, (background_id,))

        row = cursor.fetchone()
        if not row:
            return None

        bg_id, title, query, created_at = row

        # Get paragraphs
        cursor.execute("""
            SELECT paragraph_number, paragraph_text
            FROM background_paragraphs
            WHERE background_id = ?
            ORDER BY id
        """, (bg_id,))

        paragraphs = cursor.fetchall()

        return {
            'id': bg_id,
            'title': title,
            'query': query,
            'created_at': created_at,
            'paragraphs': paragraphs
        }

    def delete_background(self, background_id: int):
        """Delete a background section and its paragraphs."""
        cursor = self.conn.cursor()

        cursor.execute("DELETE FROM background_paragraphs WHERE background_id = ?", (background_id,))
        cursor.execute("DELETE FROM background_sections WHERE id = ?", (background_id,))

        self.conn.commit()

    def format_background_display(self, background: dict) -> str:
        """
        Format a background section for display with paragraph numbers.

        Args:
            background: Dictionary containing background details

        Returns:
            Formatted text string
        """
        output = f"**BACKGROUND**\n\n"

        for para_num, para_text in background['paragraphs']:
            output += f"{para_num}\t{para_text}\n\n"

        return output

    def close(self):
        """Close database connection."""
        self.conn.close()
