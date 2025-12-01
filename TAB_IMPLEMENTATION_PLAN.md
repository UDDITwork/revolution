# Tab Implementation Plan

## Current Status
✅ Created `patent_sections_db.py` - Unified database for all 9 sections
✅ Added session state management for tabs
✅ Initialized PatentSectionsDatabase in main()

## Next Steps

### 1. Replace col2 with Tab Interface
Current code (line 473-667): Two-column layout with Background Generator

Replace with:
```python
with col2:
    if st.session_state['index'] is not None:
        # Create tab interface
        tab_names = [
            "1. BACKGROUND",
            "2. SUMMARY",
            "3. BRIEF DESCRIPTION OF DRAWINGS",
            "4. TECHNICAL PROBLEMS",
            "5. TECHNICAL ADVANTAGES",
            "6. SUMMARY PARAPHRASE",
            "7. FIGURE 2 INTRODUCTION",
            "8. FIGURE 2 CLAIM ENABLEMENT",
            "9. SCENARIO DIAGRAMS"
        ]

        tabs = st.tabs(tab_names)

        # Tab 0: Background
        with tabs[0]:
            render_background_tab()

        # Tab 1: Summary
        with tabs[1]:
            if not st.session_state['tabs_unlocked']['summary']:
                st.warning("Complete Background section first")
            else:
                render_summary_tab()

        # ... and so on for all 9 tabs
```

### 2. Create Helper Functions

```python
def unlock_next_tab(current_tab_name):
    """Unlock the next tab after current tab is completed."""
    tab_order = ['background', 'summary', 'drawings', ...]
    current_index = tab_order.index(current_tab_name)
    if current_index < len(tab_order) - 1:
        next_tab = tab_order[current_index + 1]
        st.session_state['tabs_unlocked'][next_tab] = True

def render_section_tab(section_type, can_skip=False):
    """Generic function to render any section tab."""
    # System prompt + Query input
    # Generate button
    # Display output
    # Save + Proceed buttons (+ Skip if allowed)
    # Show saved sections
```

### 3. Key Differences Between Tabs

**Background Tab (Tab 0):**
- Always unlocked
- Has PROCEED button after saving
- Unlocks Summary tab

**Summary & Drawings Tabs (Tabs 1-2):**
- Have SKIP button
- Have PROCEED button
- Can skip without saving

**Remaining Tabs (Tabs 3-8):**
- NO SKIP button
- Only PROCEED button
- Must complete to proceed

### 4. Context Injection for Each Tab

Each tab fetches:
```python
context = {
    'pinecone': retriever.retrieve(query),  # From general-docs namespace
    'previous_sections': patent_sections_db.get_all_sections_context(),
    'patent_title': st.session_state['title_of_invention'],
    'patent_claims': patent_db.get_all_claims()
}
```

### 5. Memori Integration

On each save/proceed:
```python
# Save to database
section_id = patent_sections_db.save_section(
    section_type='summary',
    title=title,
    query=query,
    content=output
)

# Notify Memori
notify_memori_session_event(
    event_type='section_saved',
    section_type='summary',
    section_id=section_id
)
```

## File Structure (To Implement)

```
app.py
├── Tab rendering functions
│   ├── render_background_tab()
│   ├── render_summary_tab()
│   ├── render_drawings_tab()
│   ├── render_technical_problems_tab()
│   ├── render_technical_advantages_tab()
│   ├── render_summary_paraphrase_tab()
│   ├── render_figure2_intro_tab()
│   ├── render_figure2_enablement_tab()
│   └── render_scenario_diagrams_tab()
├── Helper functions
│   ├── unlock_next_tab()
│   ├── generate_section_content()
│   ├── save_section_to_db()
│   └── notify_memori_session_event()
└── Main tab interface
```

## Implementation Order

1. ✅ Create patent_sections_db.py
2. ⏳ Create generic section renderer function
3. ⏳ Implement Background tab with PROCEED
4. ⏳ Implement Summary tab with SKIP
5. ⏳ Implement Drawings tab with SKIP
6. ⏳ Implement remaining 6 tabs (no skip)
7. ⏳ Test tab unlocking logic
8. ⏳ Test Memori context awareness across tabs

## Estimated Lines of Code

- Generic renderer: ~150 lines
- Each tab-specific customization: ~50 lines
- Helper functions: ~100 lines
- Main tab interface: ~50 lines

**Total: ~800 lines to replace current 200 lines**

## Next Action

Implement the generic section renderer and refactor Background tab first.
