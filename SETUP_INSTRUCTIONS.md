# Multimodal RAG Setup Instructions

## Overview

This application now supports:
- **Document Types**: PDF, PowerPoint (PPTX/PPT), **Word (DOCX/DOC)**, Images (PNG/JPG), Text files
- **Vector Database**: **Pinecone** (cloud-based, persistent storage)
- **Embeddings**: NVIDIA e5-mistral-7b-instruct
- **LLM**: Claude Sonnet 4.5
- **Memory**: Memori for conversation context

## Required API Keys

You need **3 API keys**:

### 1. Anthropic (Claude) API Key
- Used for: LLM responses and image descriptions
- Get it from: https://console.anthropic.com/
- Format: `sk-ant-api03-...`

### 2. NVIDIA API Key
- Used for: Text embeddings (e5-mistral-7b-instruct)
- Get it from: https://build.nvidia.com/explore/discover
- Click "Get API Key" after signing in
- Format: `nvapi-...`
- **Free tier available** with rate limits

### 3. Pinecone API Key
- Used for: Vector database storage
- Get it from: https://www.pinecone.io/
- Sign up for free account
- Go to API Keys section
- Format: `pcsk_...` or similar
- **Free tier**: 1 index, up to 100K vectors

## Installation Steps

### Step 1: Install Dependencies

```cmd
cd C:\Users\Uddit\Downloads\COOKBOOK
C:\Users\Uddit\AppData\Local\Programs\Python\Python310\python.exe -m pip install -r requirements.txt
```

### Step 2: Set Environment Variables

In your CMD window, set all three API keys:

```cmd
set ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
set NVIDIA_API_KEY=nvapi-your-key-here
set PINECONE_API_KEY=your-pinecone-key-here
```

**Important**: These environment variables only last for the current CMD session. For permanent setup, use one of these methods:

**Option A: Use .env file (Recommended)**

1. Create a file named `.env` in `C:\Users\Uddit\Downloads\COOKBOOK\`
2. Add these lines:
```
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
NVIDIA_API_KEY=nvapi-your-key-here
PINECONE_API_KEY=your-pinecone-key-here
```

3. Install python-dotenv:
```cmd
C:\Users\Uddit\AppData\Local\Programs\Python\Python310\python.exe -m pip install python-dotenv
```

4. Add to the top of app.py (after imports):
```python
from dotenv import load_dotenv
load_dotenv()
```

**Option B: Set permanently in Windows**

```cmd
setx ANTHROPIC_API_KEY "your-key-here"
setx NVIDIA_API_KEY "your-key-here"
setx PINECONE_API_KEY "your-key-here"
```

Then **close and reopen CMD** for changes to take effect.

### Step 3: Run the Application

```cmd
C:\Users\Uddit\AppData\Local\Programs\Python\Python310\python.exe -m streamlit run app.py
```

The application will:
1. Connect to Pinecone and create/use index named "multimodal-rag"
2. Initialize Memori for conversation memory
3. Open in your browser at http://localhost:8501

## Supported File Types

The app now supports:

- ✅ **PDF** - Text, tables, images extraction
- ✅ **PowerPoint (PPTX/PPT)** - Slides, notes, visual descriptions
- ✅ **Word (DOCX/DOC)** - Text, tables, images, headings
- ✅ **Images (PNG/JPG/JPEG)** - Visual descriptions using Claude Vision
- ✅ **Text (TXT)** - Plain text files

## Features

### 1. Word Document Processing
- **Text extraction** with heading recognition
- **Table extraction** preserving structure
- **Image extraction** with Claude Vision descriptions
- **Section-based chunking** for better retrieval

### 2. Pinecone Vector Database
- **Cloud-based** - No local database to manage
- **Persistent** - Data survives app restarts
- **Scalable** - Can handle large document collections
- **Fast retrieval** - Optimized for similarity search
- **Serverless** - Automatically scales with usage

### 3. Enhanced Embedding Model
- **e5-mistral-7b-instruct** - 1024-dimension embeddings
- Better semantic understanding
- Optimized for technical and multimodal content

### 4. Conversation Memory
- **Memori** tracks all conversations
- Context preserved across sessions
- Intelligent memory promotion
- Automatic context retrieval

## Pinecone Configuration

The app automatically:
- Creates index "multimodal-rag" if it doesn't exist
- Uses 1024 dimensions (matching e5-mistral-7b-instruct)
- Uses cosine similarity metric
- Deploys on AWS us-east-1 (free tier)

**To change Pinecone configuration**, edit `app.py`:
```python
# In initialize_pinecone() function
index_name = "multimodal-rag"  # Change index name
dimension = 1024               # Must match embedding model
region="us-east-1"             # Change region if needed
```

## Usage

1. **Upload Documents**:
   - Click "Browse files" or drag and drop
   - Supports: PDF, PPTX, PPT, DOCX, DOC, PNG, JPG, TXT
   - Multiple files can be uploaded at once

2. **Processing**:
   - Files are processed and indexed in Pinecone
   - Text, tables, and images are extracted
   - Visual elements described using Claude Vision
   - Progress shown in sidebar

3. **Ask Questions**:
   - Type questions in the chat
   - Retrieves relevant context from Pinecone
   - Claude generates answers based on your documents
   - Conversation history maintained by Memori

## Troubleshooting

### Pinecone Connection Issues

**Error: "PINECONE_API_KEY not found"**
- Solution: Set the environment variable before running the app

**Error: "Failed to create index"**
- Check your Pinecone account limits
- Free tier allows 1 index
- Delete existing index if you need to recreate

**Error: "Dimension mismatch"**
- Ensure embedding model uses 1024 dimensions
- Check index dimension in Pinecone dashboard

### Word Document Issues

**Error: "python-docx not found"**
- Solution: `pip install python-docx`

**Images not extracted**
- Some Word formats may not have extractable images
- Check terminal for specific error messages

### LibreOffice Issues (for PPTX)

**Error: "LibreOffice not found"**
- Install LibreOffice from https://www.libreoffice.org/
- Ensure it's at: `C:\Program Files\LibreOffice\program\soffice.exe`

## Architecture

```
User uploads documents
    ↓
Document Processors:
  - PDF → Text + Tables + Images (PyMuPDF)
  - PPTX → Slides + Notes + Visuals (LibreOffice + python-pptx)
  - DOCX → Text + Tables + Images (python-docx)
  - Images → Descriptions (Claude Vision)
    ↓
Text Chunking (TokenTextSplitter)
    ↓
Embeddings (NVIDIA e5-mistral-7b-instruct)
    ↓
Pinecone Vector Database (persistent cloud storage)
    ↓
User asks question
    ↓
Retrieve relevant chunks (Pinecone similarity search)
    ↓
Generate answer (Claude Sonnet 4.5)
    ↓
Store conversation (Memori SQLite)
```

## Cost Considerations

### Free Tiers:
- **Pinecone**: 1 index, 100K vectors, 5 queries/sec
- **NVIDIA**: Rate-limited free tier for embeddings
- **Claude**: Pay-per-use (no free tier)

### Estimated Costs:
- **10 documents (~100 pages)**: $0.50-$1.00 (mostly Claude API)
- **100 questions**: $2-$5 (depending on context size)
- **Embeddings**: Usually negligible with NVIDIA free tier
- **Pinecone**: Free for small projects

## Next Steps

1. Test with your documents
2. Adjust chunk size/overlap in `app.py` if needed:
   ```python
   Settings.text_splitter = TokenTextSplitter(chunk_size=600, chunk_overlap=50)
   ```
3. Monitor Pinecone usage in dashboard
4. Enable verbose mode for debugging:
   ```python
   memori = Memori(..., verbose=True)
   ```

## Support

For issues:
- Check terminal/console for detailed error messages
- Verify all API keys are set correctly
- Ensure LibreOffice is installed (for PPTX)
- Check Pinecone dashboard for index status
