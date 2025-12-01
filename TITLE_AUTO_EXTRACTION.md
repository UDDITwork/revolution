# Auto-Extraction of Title of Invention

## Feature Overview

When **Input Document 2** (Patent Claims DOCX) is uploaded, the **Title of Invention** is **automatically extracted** and displayed at the top of the interface.

## How It Works

### 1. Upload Trigger
- User uploads a DOCX file to **Input Document 2**
- As soon as the file is uploaded (without clicking "Process Documents")
- Title extraction begins automatically

### 2. Extraction Process
```
Upload Input Document 2
    ↓
Auto-detect upload
    ↓
Save file temporarily
    ↓
Extract Title of Invention
    ↓
Display in text input at top
    ↓
Store in session state
```

### 3. Display Location

The title appears in a **read-only text input field** at the very top of the left column, right below "Multimodal RAG" heading.

**Visual Hierarchy:**
```
┌─────────────────────────────────┐
│ Multimodal RAG                  │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ Title of Invention:         │ │
│ │ HANDLING IN-MEMORY...       │ │  ← Title appears here
│ └─────────────────────────────┘ │
│                                 │
│ Memory System Info ▼            │
│                                 │
│ Upload Documents                │
│ ...                             │
└─────────────────────────────────┘
```

## Implementation Details

### Session State Variable

**Variable Name:** `st.session_state['title_of_invention']`

**Type:** String

**Access:**
```python
# Get the title anywhere in the code
title = st.session_state['title_of_invention']

# Check if title exists
if st.session_state.get('title_of_invention'):
    print(f"Title: {title}")
```

### Extraction Function

**Function:** `extract_title_of_invention(docx_path)`

**Location:** `patent_processor.py`

**Returns:** String (the extracted title)

**Pattern Recognition:**
- Looks for all-uppercase text
- Before "CLAIMS", "What is claimed is:", "What is defined is:"
- Usually centered in document
- Last all-caps paragraph before claims section

## Code Flow

### On File Upload

```python
# In app.py, after Input Document 2 uploader:

if input_doc2 is not None and st.session_state['title_of_invention'] is None:
    # Save uploaded file
    docx_path = save_uploaded_file(input_doc2)

    # Extract title
    title = extract_title_of_invention(docx_path)

    # Store in session state
    st.session_state['title_of_invention'] = title

    # Display success message
    st.success(f"✅ Title extracted: {title}")
```

### Display in UI

```python
# At top of left column:

if st.session_state.get('title_of_invention'):
    st.text_input(
        "Title of Invention",
        value=st.session_state['title_of_invention'],
        disabled=True,  # Read-only
        key="title_display"
    )
```

## User Experience

### Step 1: Upload Document
- User clicks "Browse files" for Input Document 2
- Selects patent claims DOCX file
- File is uploaded

### Step 2: Auto-Extraction (Immediate)
- Spinner appears: "Extracting title of invention..."
- Title is extracted from document
- Success message: "✅ Title extracted: [TITLE]"

### Step 3: Display
- Title appears in text input at top
- Text is read-only (grayed out)
- Title remains visible throughout session

### Step 4: Later Processing
- User can upload other documents
- Click "Process Documents" to index everything
- Title is already extracted and stored

## Technical Notes

### Caching
- Title is extracted **once per session**
- Condition: `if st.session_state['title_of_invention'] is None`
- If user uploads different file, need to clear session state

### Error Handling
- If extraction fails, error message is shown
- App continues to function normally
- Title field remains empty

### Storage
- **Session State**: `st.session_state['title_of_invention']`
- **Database**: `patent_claims.db` → `title_of_invention` table
- Saved to database when "Process Documents" is clicked

## Example Extraction

### Input Document
```
HANDLING IN-MEMORY APPLICATION DATA FOR APPLICATION
CONTAINERS MIGRATION

CLAIMS

What is claimed is:
1. A method, comprising:
```

### Extracted Title
```
HANDLING IN-MEMORY APPLICATION DATA FOR APPLICATION
CONTAINERS MIGRATION
```

### Display
```
┌─────────────────────────────────────────────────┐
│ Title of Invention                              │
│ HANDLING IN-MEMORY APPLICATION DATA FOR         │
│ APPLICATION CONTAINERS MIGRATION                │
└─────────────────────────────────────────────────┘
```

## Benefits

1. **Immediate Feedback**: User sees title right away
2. **No Extra Clicks**: Automatic extraction on upload
3. **Visual Confirmation**: Clear display at top of interface
4. **Persistent**: Title stays visible throughout session
5. **Accessible**: Stored in session state for easy access

## Future Enhancements

Possible improvements:
- Edit title if extraction is incorrect
- Show confidence score of extraction
- Preview full document structure
- Extract additional metadata (date, inventor, etc.)
