# Patent Document Processing Features

## New Features Added

### 1. Three Separate Document Upload Inputs

The application now supports **3 optional document uploads**:

#### **Input Document 1** (Optional - PowerPoint)
- Format: `.pptx`, `.ppt`
- Purpose: General knowledge base
- Processing: Slides extracted with visual descriptions
- Storage: Pinecone vector database

#### **Input Document 2** (Optional - Patent Claims Document)
- Format: `.docx`, `.doc`
- Purpose: **Patent claims with special processing**
- Processing:
  - **Title of Invention** extracted (text before "CLAIMS" section)
  - All **claims extracted exactly as-is** (preserving punctuation, spacing, line breaks)
  - Saved to **separate SQLite database** (`patent_claims.db`)
  - Also indexed in Pinecone for general Q&A
- Storage: **Dual storage**
  - SQLite (non-vector): Exact claims + title
  - Pinecone (vector): For semantic search

#### **Input Document 3** (Optional - Word Document)
- Format: `.docx`, `.doc`
- Purpose: Additional knowledge base
- Processing: Standard document processing (text, tables, images)
- Storage: Pinecone vector database

### 2. Patent Claims Database (SQLite)

**Database:** `patent_claims.db`

**Tables:**
- `title_of_invention`: Stores extracted title
- `claims`: Stores each claim with exact formatting

**Features:**
- Non-vector storage for exact text preservation
- Separate from conversation memory and vector search
- Preserves every comma, semicolon, period, line break
- Claims numbered and stored individually

### 3. Title of Invention Extraction

**Pattern Recognition:**
The system extracts the title by looking for:
- All uppercase text
- Located before "CLAIMS", "What is claimed is:", "What is defined is:"
- Typically centered
- Usually the last all-caps paragraph before claims section

**Example:**
```
HANDLING IN-MEMORY APPLICATION DATA FOR APPLICATION
CONTAINERS MIGRATION

CLAIMS

What is claimed is:
1. A method, comprising:
```

The system extracts: **"HANDLING IN-MEMORY APPLICATION DATA FOR APPLICATION CONTAINERS MIGRATION"**

### 4. Claims Extraction

**Exact Formatting Preservation:**
- Each claim starts with a number (1., 2., etc.)
- All punctuation preserved: `.`, `,`, `;`, `:`
- All line breaks preserved
- All spacing preserved
- Continuation lines maintained

**Example Claim Storage:**
```
1. A method, comprising:
   detecting, by a migration manager, an event to migrate a first container running on a first host to a second host;
   in response to detecting the event, determining, by the migration manager, whether the first container comprises application data comprising in-memory data structures; and
   responsive to determining that the first container comprises the application data comprising the in-memory data structures, migrating the application data.
```

Every character, space, and newline is preserved exactly as in the original document.

## How It Works

### Processing Flow

```
User uploads documents
    ↓
┌─────────────────┬──────────────────────┬─────────────────┐
│ Input Doc 1     │ Input Doc 2          │ Input Doc 3     │
│ (PPTX)          │ (DOCX - Patent)      │ (DOCX)          │
└────────┬────────┴──────────┬───────────┴────────┬────────┘
         │                   │                    │
         ↓                   ↓                    ↓
    Standard            Special Process       Standard
    Processing          ┌───────────┐         Processing
         │              │ Extract   │              │
         │              │ Title     │              │
         │              └─────┬─────┘              │
         │              ┌─────┴─────┐              │
         │              │ Extract   │              │
         │              │ Claims    │              │
         │              │ (Exact)   │              │
         │              └─────┬─────┘              │
         │                    ↓                    │
         │              Save to SQLite             │
         │              (patent_claims.db)         │
         │                    │                    │
         └────────┬───────────┴────────┬───────────┘
                  ↓                    ↓
         NVIDIA e5-mistral-7b    NVIDIA e5-mistral-7b
         Embeddings (1024-dim)   Embeddings (1024-dim)
                  ↓                    ↓
         ┌────────────────────────────────┐
         │   Pinecone Vector Database     │
         │   (multimodal-rag index)       │
         └────────────────────────────────┘
```

### Two Databases

**1. SQLite (`patent_claims.db`) - Non-Vector**
- Exact text storage
- Title of invention
- All claims with perfect formatting
- Fast direct retrieval by claim number

**2. Pinecone - Vector Database**
- Semantic search across all documents
- Embedding-based retrieval
- Similarity matching
- Cross-document Q&A

## Usage

### Upload Documents

1. Open the application
2. See three separate upload inputs
3. Upload any combination:
   - **Document 1**: PPTX (optional)
   - **Document 2**: Patent DOCX (optional, special processing)
   - **Document 3**: Additional DOCX (optional)
4. Click "Process Documents"

### View Patent Information

After processing Document 2, a new section appears:

**📄 Patent Information**
- Shows extracted title
- Shows number of claims
- Option to view all claims with exact formatting

### Ask Questions

The chatbot can now:
- Answer based on all three documents
- Reference specific patent claims
- Use title of invention in context
- Provide exact claim text when asked

## Technical Implementation

### Files Created

1. **patent_processor.py**
   - `PatentClaimsDatabase`: SQLite database handler
   - `extract_title_of_invention()`: Title extraction logic
   - `extract_claims_exact()`: Claims extraction with formatting preservation
   - `process_patent_document()`: Main processing function

### Files Modified

1. **app.py**
   - Added three separate file uploaders
   - Added patent database initialization
   - Added special processing for Document 2
   - Added patent information display

2. **requirements.txt**
   - No new requirements (uses existing `python-docx`)

## Examples

### Title Extraction Examples

**Example 1:**
```
SYSTEM AND METHOD FOR ENHANCED DATA PROCESSING

CLAIMS
What is claimed is:
```
→ Extracted: "SYSTEM AND METHOD FOR ENHANCED DATA PROCESSING"

**Example 2:**
```
HANDLING IN-MEMORY APPLICATION DATA FOR APPLICATION
CONTAINERS MIGRATION

CLAIMS
1. A method comprising:
```
→ Extracted: "HANDLING IN-MEMORY APPLICATION DATA FOR APPLICATION CONTAINERS MIGRATION"

### Claims Extraction Example

**Input:**
```
1. A method, comprising:
   step one;
   step two; and
   step three.

2. The method of claim 1, wherein:
   the step one comprises sub-steps.
```

**Stored in Database:**
- Claim 1: Entire first claim with exact spacing, semicolons, periods
- Claim 2: Entire second claim with exact formatting

## Benefits

1. **Exact Preservation**: Claims stored character-by-character as in original
2. **Dual Access**: Both semantic search (Pinecone) and exact retrieval (SQLite)
3. **Flexibility**: All inputs optional, works with any combination
4. **Compliance**: Meets legal requirements for exact claim text
5. **Organized**: Clear separation between patent claims and general documents

## Future Enhancements

Possible additions:
- Export claims to formatted document
- Compare claims across patents
- Highlight claim dependencies
- Generate claim tree visualization
- Search within specific claim numbers
