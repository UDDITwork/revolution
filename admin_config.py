"""
Admin Configuration and Prompt Management System
Handles admin authentication and system prompt storage/retrieval
Supports both local SQLite, Turso cloud database, and MongoDB for prompts.
"""

import sqlite3
import hashlib
import os
from datetime import datetime

# Try to import Turso connection
try:
    from turso_db import get_turso_connection, is_turso_enabled
    TURSO_AVAILABLE = True
except ImportError:
    TURSO_AVAILABLE = False

# Try to import MongoDB
try:
    from pymongo import MongoClient
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

def get_mongodb_client():
    """Get MongoDB client for system prompts storage"""
    mongodb_url = os.environ.get("MONGODB_URL")
    if mongodb_url and MONGODB_AVAILABLE:
        try:
            client = MongoClient(mongodb_url)
            # Test connection
            client.admin.command('ping')
            return client
        except Exception as e:
            print(f"MongoDB connection failed: {e}")
            return None
    return None

class AdminConfigDB:
    def __init__(self, db_path="admin_config.db"):
        self.db_path = db_path
        self.use_turso = TURSO_AVAILABLE and is_turso_enabled()
        # MongoDB for system prompts (separate collection)
        self.mongodb_client = get_mongodb_client()
        self.use_mongodb_for_prompts = self.mongodb_client is not None
        if self.use_mongodb_for_prompts:
            self.prompts_collection = self.mongodb_client["patragenix_db"]["system_prompts"]
            print("AdminConfig: Using MongoDB for system prompts storage")
        else:
            print("AdminConfig: Using SQLite/Turso for system prompts storage")
        self.init_database()

    def get_connection(self):
        if self.use_turso:
            return get_turso_connection("admin_config")
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """Initialize admin config database with tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Admin users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')

        # System prompts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_key TEXT UNIQUE NOT NULL,
                section_name TEXT NOT NULL,
                prompt_text TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT
            )
        ''')

        conn.commit()

        # Initialize default admin if not exists
        self._init_default_admin(cursor, conn)

        # Initialize default prompts if not exists
        self._init_default_prompts(cursor, conn)

        conn.close()

    def _hash_password(self, password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def _init_default_admin(self, cursor, conn):
        """Initialize default admin users"""
        # Admin user 1: bikash@gmail.com
        cursor.execute("SELECT COUNT(*) FROM admin_users WHERE email = ?", ("bikash@gmail.com",))
        if cursor.fetchone()[0] == 0:
            password_hash = self._hash_password("jpmcA@123")
            cursor.execute(
                "INSERT INTO admin_users (email, password_hash) VALUES (?, ?)",
                ("bikash@gmail.com", password_hash)
            )
            conn.commit()

        # Admin user 2: udditkantsinha@gmail.com
        cursor.execute("SELECT COUNT(*) FROM admin_users WHERE email = ?", ("udditkantsinha@gmail.com",))
        if cursor.fetchone()[0] == 0:
            password_hash = self._hash_password("jpmcA@123")
            cursor.execute(
                "INSERT INTO admin_users (email, password_hash) VALUES (?, ?)",
                ("udditkantsinha@gmail.com", password_hash)
            )
            conn.commit()

    def _init_default_prompts(self, cursor, conn):
        """Initialize default system prompts for all sections"""
        default_prompts = {
            "background": {
                "name": "Background Section",
                "description": "Prompt for generating the Background section of the patent",
                "prompt": """You are an expert patent writer specializing in technical documentation. Generate a comprehensive Background section for a patent application.

**Instructions:**
1. Start with paragraph number [0001] for the title
2. Use [0002] for the main background content
3. Write in formal patent language
4. Focus on the technical field and prior art context
5. Do not include specific claims or detailed implementations

**Context from documents:**
{context}

**Title of Invention:** {title}

Generate a well-structured Background section."""
            },
            "summary": {
                "name": "Summary Section",
                "description": "Prompt for generating the Summary section with 3 paragraphs",
                "prompt": """You are an expert patent writer. Your task is to convert the independent claim into a paraphrased summary format following these exact rules:

**Step 1: Opening Sentence**
Begin with: "In various embodiments of the disclosure, a [computer-implemented method/method] for [TITLE], is described."
- Use "computer-implemented method" if the claim uses this term, otherwise use "method"

**Step 2: Convert Preamble and First Claim Feature**
- Remove "A [computer-implemented method/method], comprising:" from the original claim
- Convert the first claim feature into: "The [computer-implemented method/method] includes [C1F1]."
- Remove any reference markers (e.g., [A1], [B2])

**Step 3: Convert Subsequent Claim Features**
- For each subsequent claim feature separated by ; or "; and", use: "The [computer-implemented method/method] further includes [C1Fn]."

**Step 4: Convert "wherein" Clauses**
- Replace ", wherein" with ". The" to create a new standalone sentence
- Do NOT use "includes" or "further includes" for "wherein" clauses

**Independent Claim:**
{independent_claim}

**Title:** {title}

Generate the paraphrased summary paragraph [0003]."""
            },
            "drawings": {
                "name": "Drawings Section",
                "description": "Prompt for generating Brief Description of Drawings",
                "prompt": """You are an expert patent writer. Generate the Brief Description of Drawings section.

**Instructions:**
1. For each figure, create a brief one-line description
2. Use the format: "FIG. X is a [description]"
3. Keep descriptions concise but informative
4. Reference system components where applicable

**Number of Figures:** {num_figures}
**Title of Invention:** {title}

**Context:**
{context}

Generate brief descriptions for each figure."""
            },
            "technical_problems": {
                "name": "Technical Problems Section",
                "description": "Prompt for generating Technical Problems section",
                "prompt": """You are an expert patent writer. Generate the Technical Problems section that the invention addresses.

**Instructions:**
1. Identify 3-5 key technical problems in the prior art
2. Write in formal patent language
3. Focus on limitations of existing solutions
4. Set up the need for the invention

**Title of Invention:** {title}

**Context from documents:**
{context}

Generate the Technical Problems section."""
            },
            "technical_solutions": {
                "name": "Technical Solutions Section",
                "description": "Prompt for generating Technical Solutions section",
                "prompt": """You are an expert patent writer. Generate the Technical Solutions section describing how the invention solves the identified problems.

**Instructions:**
1. Address each technical problem identified
2. Explain the novel approach of the invention
3. Highlight key technical advantages
4. Use formal patent language

**Title of Invention:** {title}

**Technical Problems:**
{technical_problems}

**Context from documents:**
{context}

Generate the Technical Solutions section."""
            },
            "technical_advantages": {
                "name": "Technical Advantages Section",
                "description": "Prompt for generating Technical Advantages section",
                "prompt": """You are an expert patent writer. Generate the Technical Advantages section highlighting the benefits of the invention.

**Instructions:**
1. List 3-5 key technical advantages
2. Be specific about improvements over prior art
3. Use measurable terms where possible
4. Maintain formal patent language

IMPORTANT RULE - "THE" WORD USAGE:
If a noun or particular word has been used in the Technical Problems section, when it appears again in Technical Advantages, use "the" before it.
Example: If "data processing system" was mentioned in Technical Problems, use "the data processing system" in Technical Advantages.

**Title of Invention:** {title}

**Context from documents:**
{context}

Generate the Technical Advantages section."""
            },
            "summary_paraphrase": {
                "name": "Summary Paraphrase Section",
                "description": "Prompt for converting patent claims to specification paragraphs",
                "prompt": """You are an expert patent writer. Convert ALL patent claims to specification paragraphs using the following EXACT template:

**INDEPENDENT CLAIM CONVERSION:**
1. Opening: "According to an aspect of the disclosure, there is provided a [method/computer-implemented method/computer system/computer program product] for [TITLE]."
2. First feature: "The [method/operations] includes [C1F1]."
3. Subsequent features: "The [method/operations] further includes [C1Fn]."
4. "wherein" clauses: Replace ", wherein" with ". The" (standalone sentence)
5. Word adjustments: "comprises" → "includes", gerunds to nouns when referenced

**DEPENDENT CLAIM CONVERSION:**
1. Remove claim references: "The method of claim X" → remove entirely
2. Replace with: "In some embodiments,"
3. "comprises/comprising" → "includes"
4. Gerund to noun: "the generating" → "the generation"
5. "wherein": ", wherein" → ". The"

**SYSTEM CLAIMS:**
- Opening: "According to an aspect of the disclosure, there is provided a computer system for [TITLE]."
- Preamble: "The computer system includes a processor set, one or more computer-readable storage media, and program instructions stored on the one or more computer-readable storage media to cause the processor set to perform operations including..."
- Subsequent operations: "The operations further include..."

**COMPUTER PROGRAM PRODUCT CLAIMS:**
- Opening: "According to an aspect of the disclosure, there is provided a computer program product for [TITLE]."
- Preamble: "The computer program product includes one or more computer-readable storage media and program instructions stored on the one or more computer-readable storage media to perform operations including..."
- Subsequent operations: "The operations further include..."

**PARAGRAPH NUMBERING:**
- Start with [0024] for independent method claim
- Each dependent claim or claim type gets its own paragraph: [0025], [0026], etc.

**IMPORTANT:**
- Preserve exact claim language (no paraphrasing of technical terms)
- Maintain order of features
- Each "wherein" clause becomes a separate sentence
- Use "the" for referenced actions/nouns"""
            },
            "figure2_intro": {
                "name": "Figure 2 Introduction",
                "description": "Prompt for generating Figure 2 introduction from uploaded image",
                "prompt": """You are an expert patent writer. Based on the Figure 2 screenshot analysis, generate an introduction paragraph for Figure 2.

**Instructions:**
1. Describe the overall system architecture shown in Figure 2
2. Identify and name the key components
3. Explain the relationships between components
4. Use formal patent language with reference numerals

**Figure 2 Analysis:**
{vision_analysis}

**Title of Invention:** {title}

**Context from documents:**
{context}

Generate the Figure 2 introduction paragraph."""
            },
            "figure2_vision": {
                "name": "Figure 2 Vision Analysis",
                "description": "Prompt for Claude Vision API to analyze Figure 2 screenshot",
                "prompt": """Analyze this patent figure (Figure 2) and extract:

1. **Components**: List all labeled components with their reference numerals (e.g., "102 - Processing Unit")
2. **Connections**: Describe how components are connected (arrows, lines, data flow)
3. **Layout**: Describe the spatial arrangement (top-to-bottom, left-to-right, hierarchical)
4. **Labels**: Extract all text labels visible in the figure
5. **Type**: Identify the diagram type (flowchart, block diagram, system architecture, etc.)

Provide a structured analysis that can be used for patent documentation."""
            },
            "sequencing": {
                "name": "Claim Feature Sequencing",
                "description": "Prompt for extracting and sequencing claim features",
                "prompt": """You are an expert patent claim analyzer. Your task is to:

**PHASE 1: CLAIM FEATURE EXTRACTION**
Break down each claim into individual features following these rules:

1. **Feature Identification:**
   - After every ";" there is a new claim feature
   - In claims with multiple features, the last feature starts after "; and" and ends before "."
   - Each feature gets a label: C#F# (Claim number, Feature number)

2. **Feature Labeling Convention:**
   - C1F1 = Claim 1, Feature 1
   - C2F3 = Claim 2, Feature 3
   - Format: C#F#{exact feature text}=[converted system description]

3. **Claim Types:**
   - **Independent Claim**: Starts with "A computer-implemented method, comprising:" or "A system, comprising:"
   - **Dependent Claim**: Refers to another claim ("The computer-implemented method of claim X...")

**PHASE 2: CONVERSION TO SYSTEM DESCRIPTIONS**

**For Independent Claims:**
- First feature (C1F1): "The system 202 is configured to {action}..."
- Subsequent features: "The system 202 is further configured to {action}..."

**For Dependent Claims with "further comprising:"**
- First feature: "In an embodiment, the system 202 is configured to {action}..."
- Subsequent features: "In an embodiment, the system 202 is further configured to {action}..."

**For Dependent Claims with "wherein the {action} comprises:"**
- "In an embodiment, to {action}, the system 202 is configured to {specific action}..."

**For Dependent Claims with "wherein the {action} further comprises:"**
- "In an embodiment, to {action}, the system 202 is further configured to {specific action}..."

**Text Handling Rules:**
1. Remove gerunds after "configured to": "tagging" → "tag", "executing" → "execute"
2. Convert "wherein" clauses to separate sentences starting with "The"
3. Change "comprise/comprises" to "include/includes" in wherein clauses
4. Remove semicolons and trailing "and" from feature text
5. Preserve exact claim language otherwise

**PHASE 3: OPERATIONAL SEQUENCING**
Arrange the converted claim features (C#F#) in the logical order of operations:
1. Analyze the flow of the invention as a complete operation
2. Determine "What step should come first?" logically
3. Order features to match the step-by-step execution flow
4. Group related features together

**OUTPUT FORMAT:**
First, output all extracted and converted features, then output the sequenced order.

Example output structure:
```
=== EXTRACTED CLAIM FEATURES ===
C1F1{feature text}=[The system 202 is configured to...]
C1F2{feature text}=[The system 202 is further configured to...]
C2F1{feature text}=[In an embodiment, the system 202 is configured to...]
...

=== SEQUENCED OPERATIONAL FLOW ===
C2F1 = [In an embodiment, the system 202 is configured to receive...]
C1F1 = [The system 202 is configured to tag...]
C1F2 = [The system 202 is further configured to execute...]
...
```

Analyze ALL claims provided and generate complete extraction and sequencing."""
            },
            "figure2_enablement": {
                "name": "Figure 2 Claim Enablement",
                "description": "Prompt for generating enablement description for each claim feature",
                "prompt": """You are an expert patent writer. Generate a detailed enablement description for the following claim feature.

**Instructions:**
1. Explain how Figure 2 enables this claim feature
2. Reference specific components from Figure 2 with reference numerals
3. Describe the technical implementation
4. Connect to the overall system architecture
5. Use formal patent language

**Claim Feature:**
{claim_feature}

**Feature ID:** {feature_id}

**Figure 2 Context:**
{fig2_context}

**Additional Context:**
{additional_context}

Generate the enablement description for this claim feature."""
            },
            "scenario_diagram": {
                "name": "Scenario Diagram Description",
                "description": "Prompt for generating scenario diagram descriptions",
                "prompt": """You are an expert patent writer. Generate a detailed description for the uploaded scenario diagram.

**Instructions:**
1. Describe the scenario flow shown in the diagram
2. Reference components with reference numerals
3. Explain the sequence of operations
4. Connect to the main system architecture (Figure 2)
5. Use formal patent language

**Scenario Number:** X_{scenario_number}

**Scenario Diagram Analysis:**
{vision_analysis}

**Figure 2 Context:**
{fig2_context}

**Additional Context:**
{additional_context}

Generate the scenario diagram description."""
            },
            "scenario_vision": {
                "name": "Scenario Diagram Vision Analysis",
                "description": "Prompt for Claude Vision API to analyze scenario diagrams",
                "prompt": """Analyze this scenario diagram and extract:

1. **Flow Steps**: List the sequence of steps/operations shown
2. **Components Involved**: Identify components referenced (with numerals if visible)
3. **Data Flow**: Describe what data/signals move between steps
4. **Decision Points**: Identify any conditional branches or decisions
5. **Start/End Points**: Identify where the scenario begins and ends

Provide a structured analysis for patent documentation."""
            }
        }

        # Initialize in MongoDB if available
        if self.use_mongodb_for_prompts:
            try:
                for section_key, config in default_prompts.items():
                    if not self.prompts_collection.find_one({"section_key": section_key}):
                        self.prompts_collection.insert_one({
                            "section_key": section_key,
                            "section_name": config["name"],
                            "prompt_text": config["prompt"],
                            "description": config["description"],
                            "updated_at": datetime.now().isoformat(),
                            "updated_by": "system"
                        })
                print("AdminConfig: Default prompts initialized in MongoDB")
            except Exception as e:
                print(f"MongoDB init prompts error: {e}")

        # Also initialize in SQLite/Turso (for fallback and local dev)
        for section_key, config in default_prompts.items():
            cursor.execute("SELECT COUNT(*) FROM system_prompts WHERE section_key = ?", (section_key,))
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    """INSERT INTO system_prompts (section_key, section_name, prompt_text, description, updated_by)
                       VALUES (?, ?, ?, ?, ?)""",
                    (section_key, config["name"], config["prompt"], config["description"], "system")
                )

        conn.commit()

    def verify_admin(self, email, password):
        """Verify admin credentials"""
        conn = self.get_connection()
        cursor = conn.cursor()

        password_hash = self._hash_password(password)
        cursor.execute(
            "SELECT id FROM admin_users WHERE email = ? AND password_hash = ?",
            (email, password_hash)
        )
        result = cursor.fetchone()

        if result:
            # Update last login (use isoformat for Turso compatibility)
            cursor.execute(
                "UPDATE admin_users SET last_login = ? WHERE id = ?",
                (datetime.now().isoformat(), result[0])
            )
            conn.commit()

        conn.close()
        return result is not None

    def get_prompt(self, section_key):
        """Get system prompt for a section"""
        # Use MongoDB if available
        if self.use_mongodb_for_prompts:
            try:
                doc = self.prompts_collection.find_one({"section_key": section_key})
                return doc["prompt_text"] if doc else None
            except Exception as e:
                print(f"MongoDB get_prompt error: {e}")
                # Fall back to SQLite

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT prompt_text FROM system_prompts WHERE section_key = ?",
            (section_key,)
        )
        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def get_all_prompts(self):
        """Get all system prompts"""
        # Use MongoDB if available
        if self.use_mongodb_for_prompts:
            try:
                results = list(self.prompts_collection.find().sort("section_name", 1))
                return [
                    {
                        "section_key": doc.get("section_key"),
                        "section_name": doc.get("section_name"),
                        "prompt_text": doc.get("prompt_text"),
                        "description": doc.get("description"),
                        "updated_at": doc.get("updated_at"),
                        "updated_by": doc.get("updated_by")
                    }
                    for doc in results
                ]
            except Exception as e:
                print(f"MongoDB get_all_prompts error: {e}")
                # Fall back to SQLite

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT section_key, section_name, prompt_text, description, updated_at, updated_by
               FROM system_prompts ORDER BY section_name"""
        )
        results = cursor.fetchall()
        conn.close()

        return [
            {
                "section_key": row[0],
                "section_name": row[1],
                "prompt_text": row[2],
                "description": row[3],
                "updated_at": row[4],
                "updated_by": row[5]
            }
            for row in results
        ]

    def update_prompt(self, section_key, prompt_text, updated_by):
        """Update a system prompt"""
        # Use MongoDB if available
        if self.use_mongodb_for_prompts:
            try:
                result = self.prompts_collection.update_one(
                    {"section_key": section_key},
                    {"$set": {
                        "prompt_text": prompt_text,
                        "updated_at": datetime.now().isoformat(),
                        "updated_by": updated_by
                    }}
                )
                return result.modified_count > 0
            except Exception as e:
                print(f"MongoDB update_prompt error: {e}")
                # Fall back to SQLite

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """UPDATE system_prompts
               SET prompt_text = ?, updated_at = ?, updated_by = ?
               WHERE section_key = ?""",
            (prompt_text, datetime.now().isoformat(), updated_by, section_key)
        )

        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def add_prompt(self, section_key, section_name, prompt_text, description, updated_by):
        """Add a new system prompt"""
        # Use MongoDB if available
        if self.use_mongodb_for_prompts:
            try:
                # Check if exists
                if self.prompts_collection.find_one({"section_key": section_key}):
                    return False  # Already exists
                self.prompts_collection.insert_one({
                    "section_key": section_key,
                    "section_name": section_name,
                    "prompt_text": prompt_text,
                    "description": description,
                    "updated_at": datetime.now().isoformat(),
                    "updated_by": updated_by
                })
                return True
            except Exception as e:
                print(f"MongoDB add_prompt error: {e}")
                # Fall back to SQLite

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """INSERT INTO system_prompts (section_key, section_name, prompt_text, description, updated_by)
                   VALUES (?, ?, ?, ?, ?)""",
                (section_key, section_name, prompt_text, description, updated_by)
            )
            conn.commit()
            success = True
        except (sqlite3.IntegrityError, Exception) as e:
            if "UNIQUE constraint" in str(e) or "IntegrityError" in str(e):
                success = False
            else:
                print(f"Error adding prompt: {e}")
                success = False

        conn.close()
        return success

    def delete_prompt(self, section_key):
        """Delete a system prompt"""
        # Use MongoDB if available
        if self.use_mongodb_for_prompts:
            try:
                result = self.prompts_collection.delete_one({"section_key": section_key})
                return result.deleted_count > 0
            except Exception as e:
                print(f"MongoDB delete_prompt error: {e}")
                # Fall back to SQLite

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM system_prompts WHERE section_key = ?", (section_key,))

        conn.commit()
        conn.close()
        return cursor.rowcount > 0
