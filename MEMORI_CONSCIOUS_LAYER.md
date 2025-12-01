# Memori as a Conscious Session Layer

## Overview
Memori acts as a **conscious, persistent memory layer** for the entire patent document generation session. It maintains awareness of all finalized backgrounds, patent claims, and session context.

## Architecture

### Memori Configuration ([app.py:108-127](app.py#L108-L127))

```python
memori = Memori(
    database_connect="sqlite:///multimodal_rag_memory.db",
    namespace="patent_generation_session",  # Dedicated namespace
    conscious_ingest=True,   # Background analysis and memory promotion
    auto_ingest=True,        # Dynamic context retrieval per query
    verbose=False
)
```

### Key Features:

#### 1. **Session-Aware Namespace**
- Namespace: `"patent_generation_session"`
- Treats entire patent document generation as a single coherent session
- Maintains continuity across multiple background generations

#### 2. **Conscious Ingest**
- Automatically promotes important information to long-term memory
- Background analysis of all API calls
- Identifies key session events (saves, updates, deletions)

#### 3. **Auto Ingest**
- Dynamically retrieves relevant context for each query
- Aware of previously finalized backgrounds
- Injects session memory into prompts

---

## How Memori Stays Aware of Saved Backgrounds

### Method 1: Direct Injection ([app.py:492-508](app.py#L492-L508))

When generating a new background, all previously saved backgrounds are injected into the prompt:

```python
saved_bg_context = inject_background_context_to_memori(
    st.session_state.get('memori'),
    st.session_state['background_db']
)

if saved_bg_context:
    enhanced_system_prompt += f"\n\n{saved_bg_context}\n\nYou are aware of all previously finalized backgrounds..."
```

**What's Injected:**
```
=== FINALIZED BACKGROUNDS IN DATABASE ===

--- Background ID: 1 ---
Title: HANDLING IN-MEMORY APPLICATION DATA...
Created: 2025-11-26 14:23:15
Query: Generate background for container management...

BACKGROUND CONTENT:
[1] The present disclosure relates to container management systems...
[2] Container management systems provide isolated execution environments...

==================================================
```

### Method 2: Session Event Notification ([app.py:573-599](app.py#L573-L599))

When a background is saved, Memori is explicitly notified:

```python
session_event = f"""
SESSION EVENT: Background Saved to Database

Background ID: {bg_id}
Title: {title}
Query: {query}...

This background is now part of the finalized patent document session memory.
All future interactions should be aware of this saved background.
"""

# Lightweight API call to inform Memori
st.session_state['anthropic_client'].messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=100,
    system="You are a session memory manager. Acknowledge this event briefly.",
    messages=[{"role": "user", "content": session_event}]
)
```

**Memori intercepts this call and:**
1. Records the session event in its memory database
2. Promotes it to long-term memory (conscious_ingest)
3. Makes it retrievable for future queries (auto_ingest)

---

## Session Context Structure

### Every Background Generation Includes:

```python
user_message = f"""SESSION CONTEXT:
This is part of an ongoing patent document generation session. You have access to:
1. Retrieved document context (from vector database)
2. Previously finalized backgrounds (if any)
3. Patent claims and title (if uploaded)

RETRIEVED CONTEXT FROM DOCUMENTS:
{context}

USER QUERY:
{background_query}

Please generate a comprehensive background section based on all available context."""
```

### Components:

1. **Retrieved Context**: Semantic search results from Pinecone
   - From `"general-docs"` namespace
   - Includes PPTX, general DOCX, and patent claims

2. **Previously Finalized Backgrounds**: All saved backgrounds from SQLite
   - With paragraph numbers [1], [2], [3]...
   - Includes metadata (ID, title, created date, query)

3. **Patent Context**: Current session patent information
   - Title of invention
   - Patent claims (from SQLite)
   - Document metadata

---

## Memori's Conscious Awareness

### What Memori Remembers:

✅ **All saved backgrounds** (via direct injection + event notification)
✅ **Patent document title** (injected in system prompt)
✅ **Previous queries** (auto_ingest from memory database)
✅ **Session events** (saves, updates, deletions)
✅ **Document processing events** (uploads, indexing)
✅ **User preferences** (system prompt modifications, query patterns)

### How It Works:

```
User Action (e.g., Save Background)
         ↓
Background saved to SQLite
         ↓
Session Event created
         ↓
API call to Claude (intercepted by Memori)
         ↓
Memori stores in memory database
         ↓
conscious_ingest promotes to long-term memory
         ↓
Future queries retrieve this context via auto_ingest
```

---

## Benefits

### 1. **Continuity Across Generations**
User can generate multiple backgrounds, and Memori maintains awareness of all previous work:

```
Generation 1: Basic background
    ↓ (saved)
Generation 2: Memori knows about Generation 1, builds upon it
    ↓ (saved)
Generation 3: Memori knows about 1 & 2, refines further
```

### 2. **Session Coherence**
The entire patent document generation is treated as one coherent session:
- Consistent terminology
- Building upon previous work
- Avoiding contradictions

### 3. **Context Preservation**
Even if user closes and reopens the app:
- Memori remembers previous session via SQLite database
- Saved backgrounds are re-injected
- Session continuity is maintained

### 4. **Intelligent Refinement**
Memori can:
- Suggest improvements based on previous backgrounds
- Identify gaps in coverage
- Maintain consistent narrative arc

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORI CONSCIOUS LAYER                   │
│  (sqlite:///multimodal_rag_memory.db)                      │
│  namespace: "patent_generation_session"                     │
└─────────────────────────────────────────────────────────────┘
                            ↕
        ┌──────────────────┴──────────────────┐
        │                                     │
        ↓                                     ↓
┌──────────────────┐              ┌──────────────────────┐
│  Background DB   │              │   Patent Claims DB   │
│   (SQLite)       │              │     (SQLite)         │
│                  │              │                      │
│ - Saved bgs with │              │ - Title of invention│
│   para numbers   │              │ - Claims (exact)    │
└──────────────────┘              └──────────────────────┘
        ↑                                     ↑
        │         Direct Injection            │
        └─────────────┬───────────────────────┘
                      │
                      ↓
            ┌──────────────────┐
            │ Claude API Call  │
            │ (Background Gen) │
            └──────────────────┘
                      ↓
              Enhanced Prompt:
              - System prompt
              - Saved backgrounds context
              - Patent title/claims
              - Retrieved documents
              - User query
```

---

## Example Session Flow

### Scenario: Generating 3 Backgrounds

**Generation 1:**
```
User Query: "Generate background for container management"
Memori Context: None (first generation)
Output: Basic background [saved as ID: 1]
Memori: Records save event
```

**Generation 2:**
```
User Query: "Add more details about edge computing"
Memori Context: Background ID 1 (container management)
Output: Enhanced background building on ID 1 [saved as ID: 2]
Memori: Records save event + knows about ID 1
```

**Generation 3:**
```
User Query: "Focus on virtual machine migration"
Memori Context: Background ID 1 + ID 2
Output: Comprehensive background incorporating all previous work [saved as ID 3]
Memori: Full session awareness of IDs 1, 2, 3
```

**Future Query:**
```
User: "What backgrounds have we created?"
Memori: Retrieves IDs 1, 2, 3 from memory
Claude: Lists all 3 with summaries, suggests next steps
```

---

## Configuration Notes

### Enabling Verbose Mode

To see Memori's internal activity:

```python
memori = Memori(
    database_connect="sqlite:///multimodal_rag_memory.db",
    namespace="patent_generation_session",
    conscious_ingest=True,
    auto_ingest=True,
    verbose=True  # ← Set to True for debugging
)
```

This will show:
- Memory ingestion events
- Context retrieval
- Session event processing

### Memory Database Location

Memori stores its memory in:
```
multimodal_rag_memory.db
```

This database persists across sessions, enabling long-term memory.

---

## Summary

Memori provides a **conscious, session-aware layer** that:

✅ Remembers all finalized backgrounds
✅ Maintains patent session context
✅ Injects relevant memory into every generation
✅ Enables iterative refinement with full context
✅ Persists across app restarts
✅ Treats patent document generation as a coherent session

This ensures that generating a complete patent document feels like a continuous, intelligent conversation rather than disconnected queries.
