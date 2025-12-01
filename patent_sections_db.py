"""
Unified database manager for all patent document sections.
Handles: Background, Summary, Drawings, Technical Problems, etc.
Supports both local SQLite and Turso cloud database.
"""
import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional, Dict
import re

# Try to import Turso connection
try:
    from turso_db import get_turso_connection, is_turso_enabled
    TURSO_AVAILABLE = True
except ImportError:
    TURSO_AVAILABLE = False

class PatentSectionsDatabase:
    """SQLite database for storing all patent document sections with paragraph numbering."""

    def __init__(self, db_path="patent_sections.db"):
        self.db_path = db_path
        self.use_turso = TURSO_AVAILABLE and is_turso_enabled()
        if self.use_turso:
            self.conn = get_turso_connection("patent_sections")
        else:
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        """Create tables for all patent sections."""
        cursor = self.conn.cursor()

        # Background sections (already exists but included for completeness)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS background_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                query TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                skipped BOOLEAN DEFAULT 0
            )
        """)

        # Add skipped column if it doesn't exist (for existing databases)
        try:
            cursor.execute("ALTER TABLE background_sections ADD COLUMN skipped BOOLEAN DEFAULT 0")
        except (sqlite3.OperationalError, Exception):
            pass  # Column already exists

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS background_paragraphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                paragraph_number TEXT,
                paragraph_text TEXT,
                FOREIGN KEY (section_id) REFERENCES background_sections(id)
            )
        """)

        # Summary sections
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summary_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                query TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                skipped BOOLEAN DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summary_paragraphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                paragraph_number TEXT,
                paragraph_text TEXT,
                FOREIGN KEY (section_id) REFERENCES summary_sections(id)
            )
        """)

        # Brief Description of Drawings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drawings_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                query TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                skipped BOOLEAN DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drawings_paragraphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                paragraph_number TEXT,
                paragraph_text TEXT,
                FOREIGN KEY (section_id) REFERENCES drawings_sections(id)
            )
        """)

        # Technical Problems (cannot skip)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS technical_problems_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                query TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                skipped BOOLEAN DEFAULT 0
            )
        """)

        try:
            cursor.execute("ALTER TABLE technical_problems_sections ADD COLUMN skipped BOOLEAN DEFAULT 0")
        except (sqlite3.OperationalError, Exception):
            pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS technical_problems_paragraphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                paragraph_number TEXT,
                paragraph_text TEXT,
                FOREIGN KEY (section_id) REFERENCES technical_problems_sections(id)
            )
        """)

        # Technical Advantages (cannot skip)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS technical_advantages_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                query TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                skipped BOOLEAN DEFAULT 0
            )
        """)

        try:
            cursor.execute("ALTER TABLE technical_advantages_sections ADD COLUMN skipped BOOLEAN DEFAULT 0")
        except (sqlite3.OperationalError, Exception):
            pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS technical_advantages_paragraphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                paragraph_number TEXT,
                paragraph_text TEXT,
                FOREIGN KEY (section_id) REFERENCES technical_advantages_sections(id)
            )
        """)

        # Summary Paraphrase (cannot skip)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summary_paraphrase_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                query TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                skipped BOOLEAN DEFAULT 0
            )
        """)

        try:
            cursor.execute("ALTER TABLE summary_paraphrase_sections ADD COLUMN skipped BOOLEAN DEFAULT 0")
        except (sqlite3.OperationalError, Exception):
            pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summary_paraphrase_paragraphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                paragraph_number TEXT,
                paragraph_text TEXT,
                FOREIGN KEY (section_id) REFERENCES summary_paraphrase_sections(id)
            )
        """)

        # Figure 2 Introduction (cannot skip)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS figure2_intro_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                query TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                skipped BOOLEAN DEFAULT 0
            )
        """)

        try:
            cursor.execute("ALTER TABLE figure2_intro_sections ADD COLUMN skipped BOOLEAN DEFAULT 0")
        except (sqlite3.OperationalError, Exception):
            pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS figure2_intro_paragraphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                paragraph_number TEXT,
                paragraph_text TEXT,
                FOREIGN KEY (section_id) REFERENCES figure2_intro_sections(id)
            )
        """)

        # Figure 2 Claim Enablement (cannot skip)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS figure2_enablement_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                query TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                skipped BOOLEAN DEFAULT 0
            )
        """)

        try:
            cursor.execute("ALTER TABLE figure2_enablement_sections ADD COLUMN skipped BOOLEAN DEFAULT 0")
        except (sqlite3.OperationalError, Exception):
            pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS figure2_enablement_paragraphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                paragraph_number TEXT,
                paragraph_text TEXT,
                FOREIGN KEY (section_id) REFERENCES figure2_enablement_sections(id)
            )
        """)

        # Scenario Diagrams (cannot skip)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scenario_diagrams_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                query TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                skipped BOOLEAN DEFAULT 0
            )
        """)

        try:
            cursor.execute("ALTER TABLE scenario_diagrams_sections ADD COLUMN skipped BOOLEAN DEFAULT 0")
        except (sqlite3.OperationalError, Exception):
            pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scenario_diagrams_paragraphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                paragraph_number TEXT,
                paragraph_text TEXT,
                FOREIGN KEY (section_id) REFERENCES scenario_diagrams_sections(id)
            )
        """)

        # Sequencing section
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sequencing_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                query TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                skipped BOOLEAN DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sequencing_paragraphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                paragraph_number TEXT,
                paragraph_text TEXT,
                FOREIGN KEY (section_id) REFERENCES sequencing_sections(id)
            )
        """)

        # Generic sections table for dynamic section types (enablement_C1F1, scenario_diagram_1, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generic_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_type TEXT,
                title TEXT,
                query TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                skipped BOOLEAN DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generic_paragraphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                paragraph_number TEXT,
                paragraph_text TEXT,
                FOREIGN KEY (section_id) REFERENCES generic_sections(id)
            )
        """)

        self.conn.commit()

    def parse_and_number_paragraphs(self, text: str) -> List[Tuple[str, str]]:
        """Parse text and add paragraph numbers [1], [2], [3], etc."""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        if len(paragraphs) <= 1:
            paragraphs = [p.strip() for p in text.split('\n') if p.strip() and len(p.strip()) > 50]

        numbered_paragraphs = []
        for idx, para in enumerate(paragraphs, start=1):
            if len(para) < 30:
                continue
            para_number = f"[{idx}]"
            numbered_paragraphs.append((para_number, para))

        return numbered_paragraphs

    def save_section(self, section_type: str, title: str, query: str, content: str, skipped: bool = False) -> int:
        """
        Save a section to the database.

        Args:
            section_type: 'background', 'summary', 'drawings', 'technical_problems', etc.
                          Also supports dynamic types: 'enablement_C1F1', 'scenario_diagram_1', etc.
            title: Patent title or section title
            query: Original query used
            content: Generated content
            skipped: Whether this section was skipped

        Returns:
            section_id: ID of saved section
        """
        cursor = self.conn.cursor()

        # Known static section types
        static_section_types = [
            'background', 'summary', 'drawings', 'technical_problems',
            'technical_advantages', 'summary_paraphrase', 'figure2_intro',
            'figure2_enablement', 'scenario_diagrams', 'sequencing'
        ]

        # Check if this is a dynamic section type
        if section_type in static_section_types:
            # Use specific tables
            section_table = f"{section_type}_sections"
            paragraphs_table = f"{section_type}_paragraphs"

            # Insert section
            cursor.execute(f"""
                INSERT INTO {section_table} (title, query, created_at, skipped)
                VALUES (?, ?, ?, ?)
            """, (title, query, datetime.now(), skipped))

            section_id = cursor.lastrowid

            # Parse and save paragraphs (only if not skipped)
            if not skipped:
                numbered_paragraphs = self.parse_and_number_paragraphs(content)

                for para_number, para_text in numbered_paragraphs:
                    cursor.execute(f"""
                        INSERT INTO {paragraphs_table} (section_id, paragraph_number, paragraph_text)
                        VALUES (?, ?, ?)
                    """, (section_id, para_number, para_text))
        else:
            # Use generic tables for dynamic section types (enablement_C1F1, scenario_diagram_1, etc.)
            cursor.execute("""
                INSERT INTO generic_sections (section_type, title, query, created_at, skipped)
                VALUES (?, ?, ?, ?, ?)
            """, (section_type, title, query, datetime.now(), skipped))

            section_id = cursor.lastrowid

            # Parse and save paragraphs (only if not skipped)
            if not skipped:
                numbered_paragraphs = self.parse_and_number_paragraphs(content)

                for para_number, para_text in numbered_paragraphs:
                    cursor.execute("""
                        INSERT INTO generic_paragraphs (section_id, paragraph_number, paragraph_text)
                        VALUES (?, ?, ?)
                    """, (section_id, para_number, para_text))

        self.conn.commit()
        return section_id

    def get_section(self, section_type: str) -> Optional[Dict]:
        """Get the latest section of a given type."""
        cursor = self.conn.cursor()

        # Known static section types
        static_section_types = [
            'background', 'summary', 'drawings', 'technical_problems',
            'technical_advantages', 'summary_paraphrase', 'figure2_intro',
            'figure2_enablement', 'scenario_diagrams', 'sequencing'
        ]

        if section_type in static_section_types:
            # Use specific tables
            section_table = f"{section_type}_sections"
            paragraphs_table = f"{section_type}_paragraphs"

            try:
                cursor.execute(f"""
                    SELECT id, title, query, created_at,
                           COALESCE(skipped, 0) as skipped
                    FROM {section_table}
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
            except (sqlite3.OperationalError, Exception):
                return None

            row = cursor.fetchone()
            if not row:
                return None

            section_id, title, query, created_at, skipped = row

            # Get paragraphs
            cursor.execute(f"""
                SELECT paragraph_number, paragraph_text
                FROM {paragraphs_table}
                WHERE section_id = ?
                ORDER BY id
            """, (section_id,))

            paragraphs = cursor.fetchall()
        else:
            # Use generic tables for dynamic section types
            try:
                cursor.execute("""
                    SELECT id, title, query, created_at,
                           COALESCE(skipped, 0) as skipped
                    FROM generic_sections
                    WHERE section_type = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (section_type,))
            except (sqlite3.OperationalError, Exception):
                return None

            row = cursor.fetchone()
            if not row:
                return None

            section_id, title, query, created_at, skipped = row

            # Get paragraphs
            cursor.execute("""
                SELECT paragraph_number, paragraph_text
                FROM generic_paragraphs
                WHERE section_id = ?
                ORDER BY id
            """, (section_id,))

            paragraphs = cursor.fetchall()

        return {
            'id': section_id,
            'type': section_type,
            'title': title,
            'query': query,
            'created_at': created_at,
            'skipped': bool(skipped),
            'paragraphs': paragraphs
        }

    def get_all_sections_context(self) -> str:
        """
        Get all saved sections formatted for Memori context injection.

        Returns a comprehensive string with all sections.
        """
        section_types = [
            'background',
            'summary',
            'drawings',
            'technical_problems',
            'technical_advantages',
            'summary_paraphrase',
            'figure2_intro',
            'sequencing',
            'figure2_enablement',
            'scenario_diagrams'
        ]

        section_names = {
            'background': 'BACKGROUND',
            'summary': 'SUMMARY',
            'drawings': 'BRIEF DESCRIPTION OF DRAWINGS',
            'technical_problems': 'TECHNICAL PROBLEMS',
            'technical_advantages': 'TECHNICAL ADVANTAGES',
            'summary_paraphrase': 'SUMMARY PARAPHRASE',
            'figure2_intro': 'FIGURE 2 INTRODUCTION',
            'sequencing': 'CLAIM SEQUENCING',
            'figure2_enablement': 'FIGURE 2 CLAIM ENABLEMENT',
            'scenario_diagrams': 'SCENARIO DIAGRAMS'
        }

        context_parts = ["=== COMPLETE PATENT DOCUMENT SECTIONS ===\n"]

        for section_type in section_types:
            section = self.get_section(section_type)
            if section:
                section_name = section_names.get(section_type, section_type.upper())

                context_parts.append(f"\n{'='*60}")
                context_parts.append(f"{section_name}")
                context_parts.append(f"{'='*60}")

                if section['skipped']:
                    context_parts.append("(SKIPPED - No content generated)\n")
                else:
                    context_parts.append(f"Title: {section['title']}")
                    context_parts.append(f"Created: {section['created_at']}\n")

                    for para_num, para_text in section['paragraphs']:
                        context_parts.append(f"{para_num} {para_text}\n")

        context_parts.append("\n" + "="*60 + "\n")

        return "\n".join(context_parts)

    def get_completion_status(self) -> Dict[str, bool]:
        """Check which sections have been completed."""
        section_types = [
            'background', 'summary', 'drawings',
            'technical_problems', 'technical_advantages',
            'summary_paraphrase', 'figure2_intro', 'sequencing',
            'figure2_enablement', 'scenario_diagrams'
        ]

        status = {}
        for section_type in section_types:
            section = self.get_section(section_type)
            status[section_type] = section is not None

        return status

    def close(self):
        """Close database connection."""
        self.conn.close()
