# Implementation Plan: Multi-Document Upload with LlamaParse

## Current State Analysis

### Existing Document Support:
- **PPTX/PPT**: ✅ Full support via `PptxReader` + LibreOffice conversion
- **DOCX/DOC**: ✅ Supported via `python-docx` in `process_docx_file()`
- **PDF**: ✅ Supported via PyMuPDF in `get_pdf_documents()`
- **Images**: ✅ Supported via Claude Vision

### Current Limitations:
1. UI restricts uploads to specific file types per uploader
2. PDF parsing uses PyMuPDF (basic) - doesn't handle complex layouts, charts, graphs well
3. No LlamaParse integration for advanced PDF/document parsing

### Key Files:
- `app.py` (lines 643-780) - Upload UI and processing logic
- `document_processors.py` - All document parsing functions
- `requirements.txt` - Dependencies

---

## Implementation Plan

### Phase 1: Update Dependencies

**File: `requirements.txt`**
Add:
```
llama-parse
```

This provides LlamaParse for advanced PDF/document parsing with:
- Chart/graph extraction
- Complex table recognition
- Better layout understanding
- Auto-mode for cost optimization

---

### Phase 2: Create LlamaParse Document Processor

**New File: `llamaparse_processor.py`**

Create a new processor that uses LlamaParse for enhanced document parsing:

```python
# Key Functions:
1. get_llamaparse_client()
   - Initialize LlamaParse with API key from env (LLAMA_CLOUD_API_KEY)
   - Configure auto_mode, extract_charts, etc.

2. parse_document_with_llamaparse(file_path, file_type) -> List[Document]
   - Parse PDF/DOCX using LlamaParse
   - Return markdown output
   - Convert to LlamaIndex Documents
   - Handle charts/tables specially

3. should_use_llamaparse(file_type) -> bool
   - Return True for PDF files (primary use case)
   - Optional for DOCX (can fall back to python-docx)
```

**LlamaParse Configuration:**
```python
parser = LlamaParse(
    api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
    result_type="markdown",
    extract_charts=True,
    auto_mode=True,
    auto_mode_trigger_on_image_in_page=True,
    auto_mode_trigger_on_table_in_page=True,
)
```

---

### Phase 3: Update Upload UI

**File: `app.py` (lines 643-685)**

Change the upload interface to accept multiple document types:

**BEFORE:**
```python
# Input Document 1: PowerPoint (Optional)
st.markdown("**Input Document 1** (Optional - PPTX)")
input_doc1 = st.file_uploader(
    "Upload PowerPoint presentation",
    type=['pptx', 'ppt'],
    ...
)
```

**AFTER:**
```python
# Input Document 1: Any supported document
st.markdown("**Input Document 1** (Optional)")
input_doc1 = st.file_uploader(
    "Upload document (PDF, PPTX, DOCX, or Image)",
    type=['pptx', 'ppt', 'pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg'],
    key="input_doc1",
    help="Supports: PowerPoint, PDF, Word documents, and images"
)

# Input Document 2: Patent Claims (keep specific for patent extraction)
# ... keep as DOCX only for patent claim extraction logic

# Input Document 3: Any supported document
st.markdown("**Input Document 3** (Optional)")
input_doc3 = st.file_uploader(
    "Upload additional document (PDF, PPTX, DOCX, or Image)",
    type=['pptx', 'ppt', 'pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg'],
    key="input_doc3",
    help="Supports: PowerPoint, PDF, Word documents, and images"
)
```

---

### Phase 4: Update Document Processing Pipeline

**File: `document_processors.py`**

Modify `load_multimodal_data()` to use LlamaParse for PDFs:

```python
def load_multimodal_data(files, llm):
    documents = []
    for file in files:
        file_extension = os.path.splitext(file.name.lower())[1]

        if file_extension == '.pdf':
            # Try LlamaParse first (better quality)
            try:
                from llamaparse_processor import parse_with_llamaparse
                if is_llamaparse_available():
                    docs = parse_with_llamaparse(file)
                    documents.extend(docs)
                    continue
            except Exception as e:
                print(f"LlamaParse failed, falling back to PyMuPDF: {e}")

            # Fallback to existing PyMuPDF processing
            pdf_documents = get_pdf_documents(file, llm)
            documents.extend(pdf_documents)

        # ... rest of existing logic for PPTX, DOCX, images
```

---

### Phase 5: Chunking and Embedding (Already Handled)

The existing pipeline already handles chunking and embedding:

**Current Settings (app.py lines 258-270):**
```python
Settings.embed_model = NVIDIAEmbedding(
    model="nvidia/llama-3.2-nv-embedqa-1b-v2",  # 2048-dim
    truncate="END"
)

Settings.text_splitter = TokenTextSplitter(
    chunk_size=600,      # 600 tokens per chunk
    chunk_overlap=50     # 50 tokens overlap
)
```

**No changes needed** - LlamaParse returns markdown text which flows through the existing pipeline:
1. LlamaParse → Markdown text
2. Convert to LlamaIndex `Document` objects
3. `VectorStoreIndex.from_documents()` automatically:
   - Chunks using `Settings.text_splitter`
   - Embeds using `Settings.embed_model`
   - Stores in Pinecone

---

### Phase 6: Environment Variables

**Required env vars:**
```
LLAMA_CLOUD_API_KEY=llx-...  # Get from LlamaCloud account
```

**Add to `run_local.bat`:**
```batch
set LLAMA_CLOUD_API_KEY=your_llama_cloud_api_key_here
```

**Add to Render environment variables** for production deployment.

---

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `requirements.txt` | MODIFY | Add `llama-parse` |
| `llamaparse_processor.py` | CREATE | New LlamaParse processor module |
| `app.py` | MODIFY | Update file uploaders to accept multiple types |
| `document_processors.py` | MODIFY | Integrate LlamaParse with fallback to PyMuPDF |
| `run_local.bat` | MODIFY | Add `LLAMA_CLOUD_API_KEY` env var |

---

## Implementation Order

1. **Add `llama-parse` to requirements.txt**
2. **Create `llamaparse_processor.py`** with:
   - LlamaParse initialization
   - Document parsing function
   - Markdown to Document conversion
3. **Update `document_processors.py`**:
   - Import llamaparse_processor
   - Modify `load_multimodal_data()` to try LlamaParse for PDFs
   - Keep PyMuPDF as fallback
4. **Update `app.py`**:
   - Change file_uploader types to accept all supported formats
   - Update help text
5. **Update `run_local.bat`**:
   - Add LLAMA_CLOUD_API_KEY placeholder
6. **Test locally** with sample PDF containing charts/tables
7. **Commit and push** to GitHub
8. **Add env var to Render** for production

---

## Key Technical Decisions

### Why LlamaParse over PyMuPDF for PDFs?
| Feature | PyMuPDF (Current) | LlamaParse (New) |
|---------|-------------------|------------------|
| Basic text | ✅ Good | ✅ Excellent |
| Tables | ⚠️ Basic | ✅ Advanced |
| Charts/Graphs | ❌ No extraction | ✅ Extracts data |
| Complex layouts | ⚠️ May fail | ✅ AI-powered |
| Cost | Free | API-based (free tier available) |

### Fallback Strategy
- LlamaParse fails → Fall back to PyMuPDF
- No API key → Use PyMuPDF
- Network issues → Use PyMuPDF

### Namespace Strategy (Unchanged)
- `general-docs`: All non-patent documents
- `patent-claims`: Patent claims specifically

---

## Dependencies

**New:**
- `llama-parse` - LlamaParse SDK

**Existing (no changes):**
- `llama-index-core` - Document indexing
- `llama-index-embeddings-nvidia` - NVIDIA embeddings
- `llama-index-vector-stores-pinecone` - Pinecone storage
- `pymupdf` - PDF fallback
- `python-pptx` - PowerPoint parsing
- `python-docx` - Word parsing

---

## Testing Plan

1. **Unit Tests:**
   - Test LlamaParse with sample PDF (charts, tables)
   - Test fallback when LlamaParse unavailable
   - Test all file type detection

2. **Integration Tests:**
   - Upload PDF → verify chunking → verify Pinecone storage
   - Upload PPTX → verify slide extraction
   - Upload DOCX → verify section extraction
   - Mix of document types

3. **Manual Testing:**
   - Upload complex PDF with charts
   - Verify markdown output quality
   - Query indexed content to verify retrieval

---

## Estimated Effort

- Phase 1 (Dependencies): 5 minutes
- Phase 2 (LlamaParse Processor): 30 minutes
- Phase 3 (UI Update): 15 minutes
- Phase 4 (Pipeline Integration): 20 minutes
- Phase 5 (Already done): 0 minutes
- Phase 6 (Env vars): 5 minutes
- Testing: 30 minutes

**Total: ~2 hours**
