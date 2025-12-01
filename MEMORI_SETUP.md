# Memori Integration - Persistent Conversation Memory

This Multimodal RAG application now includes **Memori** for intelligent, persistent conversation memory across sessions.

## What is Memori?

Memori is an open-source memory engine that enables LLMs to:
- **Remember conversations** across sessions
- **Learn from interactions** and prioritize important information
- **Maintain context** automatically without manual prompting
- Store memory in **SQL databases you control** (SQLite, PostgreSQL, MySQL)

## How It Works in This App

### Dual-Mode Memory System

1. **Conscious Mode** (Background Analysis)
   - Background "conscious agent" analyzes conversations every 6 hours
   - Automatically promotes essential memories from long-term to short-term storage
   - Categorizes information: facts, preferences, skills, rules, context

2. **Auto Mode** (Dynamic Retrieval)
   - Dynamically searches and injects relevant context for each query
   - No manual memory management needed
   - Context-aware responses based on past conversations

### Architecture Flow

```
User Query → Memori intercepts → Retrieves relevant memories → Injects context → LLM receives enriched query
                ↓
LLM Response → Memori records → Extracts entities → Stores in SQLite → Returns response to user
                ↓
Background (every 6 hours) → Conscious Agent analyzes patterns → Promotes essential memories
```

## Installation

### 1. Install memorisdk

```bash
# Activate your virtual environment first
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install memorisdk
pip install memorisdk
```

### 2. Set Required API Keys

This app uses **Claude (Anthropic)** for everything - including the Memori conscious agent!

**Option A: Environment Variables**
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

**Option B: Create `.env` file**
```bash
# Create .env file in the COOKBOOK directory
ANTHROPIC_API_KEY=sk-ant-your-claude-key-here
NVIDIA_API_KEY=nvapi-your-nvidia-key-here
```

**API Keys Required:**
- **ANTHROPIC_API_KEY**: For Claude Sonnet 4.5 (LLM + Vision + Memori conscious agent)
- **NVIDIA_API_KEY**: For NV-EmbedQA-E5-V5 embeddings

### 3. Run the Application

```bash
streamlit run app.py
```

You should see:
- ✅ "Memori enabled - conversations will be remembered across sessions!" in the sidebar
- 🧠 Memory System Info expandable panel

**Note:** No OpenAI API key needed! Everything runs on Claude Sonnet 4.5.

## Features Enabled by Memori

### 1. Cross-Session Memory
- Upload a PPTX file in Session 1
- Ask questions about it
- Close the browser
- Come back later in Session 2
- **The system remembers your previous questions and context!**

### 2. Intelligent Context Injection
**Without Memori:**
- User: "What did we discuss about the implementation flow?"
- System: "I don't have information about previous discussions."

**With Memori:**
- User: "What did we discuss about the implementation flow?"
- System: "Earlier you asked about Slide 11's implementation flow, which showed the 6-step process..."

### 3. Personalized Responses
- Memori learns your preferences over time
- Remembers which slides you found most interesting
- Adapts responses based on your previous questions

## Configuration

The Memori configuration is in [app.py](app.py:42-61):

```python
@st.cache_resource
def initialize_memori():
    """Initialize Memori for persistent conversation memory using Claude."""
    from memori import ProviderConfig

    # Configure Memori to use Claude/Anthropic instead of OpenAI
    provider_config = ProviderConfig.from_anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-sonnet-4-20250514"  # Use same model as main LLM
    )

    memori = Memori(
        database_connect="sqlite:///multimodal_rag_memory.db",
        namespace="multimodal_rag",
        conscious_ingest=True,  # Background analysis
        auto_ingest=True,       # Dynamic context retrieval
        verbose=False,          # Set to True to see agent activity
        provider_config=provider_config  # Use Claude for conscious agent
    )
    memori.enable()
    return memori
```

### Configuration Options

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `database_connect` | `sqlite:///multimodal_rag_memory.db` | Local SQLite database for memory storage |
| `namespace` | `multimodal_rag` | Separate memory space from other apps |
| `conscious_ingest` | `True` | Enable background memory analysis and promotion |
| `auto_ingest` | `True` | Enable dynamic context retrieval per query |
| `verbose` | `False` | Set to `True` to see agent activity logs |
| `provider_config` | `ProviderConfig.from_anthropic()` | Use Claude Sonnet 4.5 for conscious agent |

### Advanced Configuration

**Use PostgreSQL instead of SQLite:**
```python
memori = Memori(
    database_connect="postgresql://user:pass@localhost/memori",
    # ... other settings
)
```

**Enable verbose logging:**
```python
memori = Memori(
    # ... other settings
    verbose=True  # Shows agent activity in console
)
```

## Memory Database

All conversations are stored in `multimodal_rag_memory.db` (SQLite).

**Database location:** `c:\Users\Uddit\Downloads\COOKBOOK\multimodal_rag_memory.db`

### View Memory Contents

You can query the database directly using SQLite tools:

```bash
# Install sqlite3 CLI
# Windows: Download from https://www.sqlite.org/download.html

# Query the database
sqlite3 multimodal_rag_memory.db "SELECT * FROM conversations LIMIT 10;"
```

### Export Memory

Since Memori uses standard SQL, you can easily export and migrate your memory:

```bash
# Export to SQL dump
sqlite3 multimodal_rag_memory.db .dump > memory_backup.sql

# Import to PostgreSQL
psql -U user -d memori < memory_backup.sql
```

## How Memori Complements the RAG Pipeline

### Current System (Document Retrieval)
- **Purpose:** "What's in this document?"
- **Scope:** Uploaded files (PPTX, PDF, images)
- **Storage:** Vector embeddings (NVIDIA NV-EmbedQA)
- **Lifetime:** Session-based (resets on restart)

### Memori (Conversation Memory)
- **Purpose:** "What did we discuss before?"
- **Scope:** All conversations and interactions
- **Storage:** SQL database with full-text search
- **Lifetime:** Persistent across sessions

**Together they provide:**
1. **Document search** - Find information in uploaded files
2. **Conversation context** - Remember past discussions
3. **Personalization** - Learn user preferences and patterns
4. **Continuity** - Seamless experience across sessions

## Cost Savings

Memori provides **80-90% cost savings** compared to traditional vector-based memory systems:
- No expensive vector embeddings for conversations
- SQL queries instead of vector similarity search
- Efficient indexing and retrieval

## Troubleshooting

### Issue: "Memori initialization failed"

**Cause:** Missing Anthropic API key

**Solution:**
```bash
# Set the Anthropic API key
set ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Issue: "Database locked" error

**Cause:** Multiple Streamlit instances accessing the same database

**Solution:**
- Close all Streamlit instances
- Delete `multimodal_rag_memory.db`
- Restart the app

### Issue: Verbose logs cluttering output

**Cause:** `verbose=True` in Memori config

**Solution:**
- Change `verbose=False` in [app.py](app.py:49)
- Restart the app

## Examples

### Example 1: Context Preservation

**Session 1:**
```
User: Upload P202500721 v3.0.pptx
User: What is Implement 6 about?
System: [Provides answer about Implement 6 flowchart]
```

**Session 2 (next day):**
```
User: Can you remind me about that implementation flow we discussed yesterday?
System: You asked about Implement 6, which describes the [detailed answer]...
```

### Example 2: Preference Learning

**Over multiple sessions:**
```
User: I'm particularly interested in the architecture diagrams.
User: Show me more flowcharts like the previous ones.
User: Can you explain the system architecture?

[Memori learns: User prefers visual/architectural content]

Future queries automatically prioritize architecture-related context!
```

## Learn More

- **Memori Documentation:** https://github.com/GibsonAI/memori
- **Memori Website:** https://memorilabs.ai
- **LlamaIndex Docs:** https://docs.llamaindex.ai
- **Claude API:** https://docs.anthropic.com

## Support

For issues specific to:
- **Memori:** https://github.com/GibsonAI/memori/issues
- **This app:** Check console logs and error messages
