# Quick Start Guide - Multimodal RAG with Memori

## Installation (5 minutes)

### 1. Activate Virtual Environment
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Install Memori
```bash
pip install memorisdk
```

### 3. Set API Keys
```bash
# Windows Command Prompt
set ANTHROPIC_API_KEY=sk-ant-your-claude-key-here
set NVIDIA_API_KEY=nvapi-your-nvidia-key-here

# Windows PowerShell
$env:ANTHROPIC_API_KEY="sk-ant-your-claude-key-here"
$env:NVIDIA_API_KEY="nvapi-your-nvidia-key-here"

# Linux/Mac
export ANTHROPIC_API_KEY=sk-ant-your-claude-key-here
export NVIDIA_API_KEY=nvapi-your-nvidia-key-here
```

### 4. Run the App
```bash
streamlit run app.py
```

## What You Get

### Pure Claude Setup
- **LLM**: Claude Sonnet 4.5 (text generation)
- **Vision**: Claude Sonnet 4.5 (image descriptions)
- **Memory Agent**: Claude Sonnet 4.5 (Memori conscious agent)
- **Embeddings**: NVIDIA NV-EmbedQA-E5-V5

**No OpenAI API key required!**

### Features
✅ Upload PPTX/PDF/Images
✅ Visual content analysis (flowcharts, diagrams)
✅ Question answering with RAG
✅ **Cross-session conversation memory**
✅ **Intelligent context preservation**

## Usage

### First Session
1. Upload your PPTX file
2. Wait for processing (with visual descriptions)
3. Ask questions: "What is Implement 6 about?"
4. Close the browser

### Next Session (even days later!)
1. Open the app again
2. Ask: "What did we discuss about implementation flows?"
3. **Memori remembers and provides context!**

## Memory System

### How It Works
- **Conscious Mode**: Background agent (runs every 6 hours) analyzes conversations and promotes important memories
- **Auto Mode**: Dynamically retrieves relevant context for each query
- **Storage**: SQLite database (`multimodal_rag_memory.db`)

### What Gets Remembered
- Previous questions you asked
- Document topics you're interested in
- Patterns in your queries
- Preferences (e.g., focus on architecture diagrams)

## Troubleshooting

### App doesn't start
```bash
# Check if API keys are set
echo %ANTHROPIC_API_KEY%  # Windows CMD
echo $ANTHROPIC_API_KEY   # Linux/Mac/PowerShell
```

### "Memori initialization failed"
- Make sure `ANTHROPIC_API_KEY` is set
- Run: `pip install --upgrade memorisdk`

### LibreOffice errors (PPTX processing)
- Install LibreOffice: https://www.libreoffice.org/download/
- Restart terminal after installation

## Cost Efficiency

### With Memori
- **80-90% cost savings** vs traditional vector memory
- No embedding costs for conversations
- SQL queries instead of vector search

### Typical Costs (18-slide PPTX)
- Processing: ~$0.50 (one-time, Claude Vision for 18 images)
- Embeddings: ~$0.01 (NVIDIA NV-EmbedQA)
- Query (with memory): ~$0.02-0.05 per query
- **Memory storage**: Free (SQLite)

## Architecture

```
User Query
    ↓
Memori (retrieves past context)
    ↓
LlamaIndex RAG (retrieves from documents)
    ↓
Claude Sonnet 4.5 (generates response)
    ↓
Memori (stores conversation)
    ↓
Response to User
```

## Files Created

```
COOKBOOK/
├── app.py                              # Main Streamlit app (Memori enabled)
├── multimodal_rag_memory.db           # Memori conversation database
├── vectorstore/
│   ├── ppt_references/                # Converted PDFs and images
│   ├── table_references/              # Extracted tables
│   └── image_references/              # Extracted images
```

## Learn More

- **Full Setup Guide**: [MEMORI_SETUP.md](MEMORI_SETUP.md)
- **Memori GitHub**: https://github.com/GibsonAI/memori
- **Claude API Docs**: https://docs.anthropic.com
- **LlamaIndex Docs**: https://docs.llamaindex.ai

## Support

If you encounter issues:
1. Check the terminal/console for detailed error messages
2. Verify API keys are set correctly
3. Ensure LibreOffice is installed for PPTX processing
4. Check [MEMORI_SETUP.md](MEMORI_SETUP.md) for detailed troubleshooting
