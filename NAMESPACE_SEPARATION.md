# Pinecone Namespace Separation

## Overview
The application uses **Pinecone namespaces** to keep patent claims and invention details completely separated in the vector database.

## Architecture

### Single Pinecone Index: `multimodal-rag`
- **Dimension**: 2048
- **Metric**: Cosine similarity
- **Cloud**: AWS (us-east-1)

### Two Separate Namespaces:

#### 1. **`general-docs` Namespace**
**Contains:**
- Input Document 1 (PPTX) - PowerPoint slides with invention details
- Input Document 3 (DOCX) - General Word documents with invention background
- Any other general documentation

**Used for:**
- Background generation
- General Q&A about the invention
- Understanding technical context

**Access:**
- `st.session_state['index']` - retriever points to this namespace

---

#### 2. **`patent-claims` Namespace**
**Contains:**
- Input Document 2 (Patent Claims DOCX) - ONLY the patent claims document
- Claims text with exact formatting preserved

**Used for:**
- Semantic search within claims only
- Claims analysis
- Prior art comparison (if needed)

**Access:**
- `st.session_state['claims_index']` - separate retriever for claims only

---

## Why Separate Namespaces?

### Without Separation (❌ Problem):
```
Pinecone Index
├── PPTX slides (invention details)
├── Patent claims
└── General docs
     ↓
When searching: Claims mixed with invention details
Results: Confusing, claims contaminate background context
```

### With Namespace Separation (✅ Solution):
```
Pinecone Index
├── Namespace: "general-docs"
│   ├── PPTX slides
│   └── General DOCX
│
└── Namespace: "patent-claims"
    └── Patent claims ONLY
     ↓
When searching "general-docs": Only invention details
When searching "patent-claims": Only claims
Results: Clean separation, no cross-contamination
```

## Benefits

1. **No Mixing**: Patent claims never contaminate background generation
2. **Targeted Search**: Search claims separately from invention details
3. **Same Index**: Both namespaces share the same Pinecone index (cost-effective)
4. **Independent Retrieval**: Each namespace has its own retriever
5. **SQLite + Pinecone**: Claims also saved in SQLite for exact text retrieval

## Implementation Details

### Code Location: [app.py](app.py#L342-L360)

```python
# General documents → "general-docs" namespace
if all_documents:
    st.session_state['index'] = create_index(
        all_documents,
        st.session_state['pinecone_index'],
        namespace="general-docs"  # ← Separate namespace
    )

# Patent claims → "patent-claims" namespace
if patent_claims_docs:
    st.session_state['claims_index'] = create_index(
        patent_claims_docs,
        st.session_state['pinecone_index'],
        namespace="patent-claims"  # ← Separate namespace
    )
```

### Function Signature: [app.py](app.py#L135)

```python
def create_index(documents, pinecone_index, namespace="general-docs"):
    """
    Create vector index with namespace support.

    Args:
        namespace: "general-docs" or "patent-claims"
    """
    vector_store = PineconeVectorStore(
        pinecone_index=pinecone_index,
        namespace=namespace  # ← Pinecone namespace parameter
    )
```

## Storage Summary

| Content Type | SQLite Database | Pinecone Namespace | Purpose |
|--------------|----------------|-------------------|---------|
| **Patent Title** | `patent_claims.db` | - | Exact text storage |
| **Patent Claims** | `patent_claims.db` | `patent-claims` | Exact text + semantic search |
| **PPTX Slides** | - | `general-docs` | Semantic search for background |
| **General DOCX** | - | `general-docs` | Semantic search for background |
| **Background Sections** | `background_sections.db` | - | Saved finalized backgrounds |

## Querying

### For Background Generation (uses `general-docs` namespace):
```python
retriever = st.session_state['index'].as_retriever(similarity_top_k=5)
# Only searches PPTX and general DOCX, NO claims contamination
```

### For Claims Analysis (uses `patent-claims` namespace):
```python
claims_retriever = st.session_state['claims_index'].as_retriever(similarity_top_k=5)
# Only searches patent claims
```

## Result

✅ **Clean separation** between claims and invention details
✅ **No cross-contamination** during background generation
✅ **Targeted searches** in each namespace independently
✅ **Cost-efficient** using single Pinecone index with namespaces
