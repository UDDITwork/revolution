# SPDX-FileCopyrightText: Copyright (c) 2023-2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# MUST BE FIRST: Fix sqlite3 import for Windows systems without built-in sqlite3
import sqlite_fix

import os
import streamlit as st
from llama_index.core import Settings, VectorStoreIndex, StorageContext
from llama_index.embeddings.nvidia import NVIDIAEmbedding
from llama_index.llms.anthropic import Anthropic
from llama_index.vector_stores.pinecone import PineconeVectorStore
from document_processors import load_multimodal_data, load_data_from_directory
from memori import Memori
from anthropic import Anthropic as AnthropicClient
from pinecone import Pinecone, ServerlessSpec
from patent_processor import PatentClaimsDatabase, process_patent_document
from background_database import BackgroundDatabase
from patent_sections_db import PatentSectionsDatabase
from admin_config import AdminConfigDB
from patent_context_manager import PatentContextManager, build_enhanced_system_prompt

# Initialize session state variables for managing chat history and document index
if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'index' not in st.session_state:
    st.session_state['index'] = None  # For general documents (PPTX, general DOCX)
if 'claims_index' not in st.session_state:
    st.session_state['claims_index'] = None  # Separate index for patent claims
if 'memori_initialized' not in st.session_state:
    st.session_state['memori_initialized'] = False
if 'anthropic_client' not in st.session_state:
    st.session_state['anthropic_client'] = None
if 'pinecone_initialized' not in st.session_state:
    st.session_state['pinecone_initialized'] = False
if 'pinecone_index' not in st.session_state:
    st.session_state['pinecone_index'] = None
if 'patent_db' not in st.session_state:
    st.session_state['patent_db'] = None
if 'patent_processed' not in st.session_state:
    st.session_state['patent_processed'] = False
if 'title_of_invention' not in st.session_state:
    st.session_state['title_of_invention'] = None
if 'background_db' not in st.session_state:
    st.session_state['background_db'] = None
if 'current_background_output' not in st.session_state:
    st.session_state['current_background_output'] = None

# TAB STATE MANAGEMENT - Track which tabs are unlocked and completed
if 'patent_sections_db' not in st.session_state:
    st.session_state['patent_sections_db'] = None
if 'active_tab' not in st.session_state:
    st.session_state['active_tab'] = 0  # Start with Background tab
if 'tabs_unlocked' not in st.session_state:
    # Background is always unlocked, others unlock as user progresses
    st.session_state['tabs_unlocked'] = {
        'background': True,
        'summary': False,
        'drawings': False,
        'technical_problems': False,
        'technical_advantages': False,
        'summary_paraphrase': False,
        'figure2_intro': False,
        'sequencing': False,
        'figure2_enablement': False,
        'scenario_diagrams': False
    }
if 'current_section_output' not in st.session_state:
    st.session_state['current_section_output'] = {}  # Stores outputs for each section
if 'fig2_image_uploaded' not in st.session_state:
    st.session_state['fig2_image_uploaded'] = False
if 'fig2_vision_data' not in st.session_state:
    st.session_state['fig2_vision_data'] = None
if 'fig2_image_bytes' not in st.session_state:
    st.session_state['fig2_image_bytes'] = None
if 'fig2_index' not in st.session_state:
    st.session_state['fig2_index'] = None
if 'claim_features_extracted' not in st.session_state:
    st.session_state['claim_features_extracted'] = None
if 'sequencing_output' not in st.session_state:
    st.session_state['sequencing_output'] = None
if 'sequenced_features_list' not in st.session_state:
    st.session_state['sequenced_features_list'] = []  # List of (feature_id, feature_text) tuples
if 'custom_order_modified' not in st.session_state:
    st.session_state['custom_order_modified'] = False
if 'current_feature_index' not in st.session_state:
    st.session_state['current_feature_index'] = 0  # Track which claim feature is currently being enabled
if 'enabled_features' not in st.session_state:
    st.session_state['enabled_features'] = {}  # Store enabled feature outputs {feature_id: output_text}
if 'current_feature_output' not in st.session_state:
    st.session_state['current_feature_output'] = ""  # Current editable output for active feature
if 'all_features_enabled' not in st.session_state:
    st.session_state['all_features_enabled'] = False
if 'scenario_diagrams_count' not in st.session_state:
    st.session_state['scenario_diagrams_count'] = 0  # Track number of scenario diagrams
if 'scenario_outputs' not in st.session_state:
    st.session_state['scenario_outputs'] = {}  # Store outputs for each scenario diagram
if 'current_scenario_index' not in st.session_state:
    st.session_state['current_scenario_index'] = 0  # Track current scenario being processed

# Admin configuration for system prompts
if 'admin_config_db' not in st.session_state:
    st.session_state['admin_config_db'] = AdminConfigDB()

# Patent Context Manager for antecedent basis tracking
if 'patent_context_manager' not in st.session_state:
    st.session_state['patent_context_manager'] = None  # Initialize after DBs are ready

# Set up the page configuration
st.set_page_config(layout="wide")

# Initialize Claude Sonnet 4.5 (best-in-class for RAG)
@st.cache_resource
def initialize_llm():
    llm = Anthropic(model="claude-sonnet-4-20250514", api_key=os.getenv("ANTHROPIC_API_KEY"))
    return llm

@st.cache_resource
def initialize_pinecone():
    """Initialize Pinecone vector database."""
    try:
        # Get Pinecone API key from environment
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        if not pinecone_api_key:
            raise ValueError("PINECONE_API_KEY not found in environment variables")

        # Initialize Pinecone
        pc = Pinecone(api_key=pinecone_api_key)

        # Index configuration
        index_name = "multimodal-rag"
        dimension = 2048  # llama-3.2-nv-embedqa-1b-v2 default dimension is 2048

        # Check if index exists, create if not
        existing_indexes = pc.list_indexes().names()
        if index_name not in existing_indexes:
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            print(f"Created new Pinecone index: {index_name}")
        else:
            print(f"Using existing Pinecone index: {index_name}")

        # Get the index
        pinecone_index = pc.Index(index_name)
        return pinecone_index

    except Exception as e:
        print(f"Error initializing Pinecone: {e}")
        raise

@st.cache_resource
def initialize_memori():
    """
    Initialize Memori for patent document generation sessions.

    Architecture:
    - Memori uses OpenAI for internal memory agents (conscious_ingest, auto_ingest)
    - Your app uses Anthropic (Claude) for patent document generation
    - LiteLLM bridges both - records all conversations automatically

    Environment Detection:
    - Production (Render): Uses PostgreSQL via MEMORI_DATABASE_URL
    - Local Development: Uses SQLite (memori_patent.db)
    """
    # Detect environment: PostgreSQL for production, SQLite for local
    database_url = os.environ.get("MEMORI_DATABASE_URL", "")

    if database_url:
        # Production: Use PostgreSQL from Render
        print("Memori: Using PostgreSQL database (production)")
    else:
        # Local development: Use SQLite
        database_url = "sqlite:///memori_patent.db"
        print("Memori: Using SQLite database (local development)")

    try:
        # Get OpenAI API key for Memori's internal agents
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            print("WARNING: OPENAI_API_KEY not found - Memori features will be limited")

        # Initialize Memori with full features
        # - database_connect: PostgreSQL (prod) or SQLite (local)
        # - conscious_ingest: AI-powered memory analysis at startup
        # - auto_ingest: Automatic context injection on every LLM call
        # - openai_api_key: For Memori's internal memory processing agents
        memori = Memori(
            database_connect=database_url,
            namespace="patent_generation_session",
            conscious_ingest=True,   # Enable background memory analysis
            auto_ingest=True,        # Enable automatic context injection
            openai_api_key=openai_api_key,
            verbose=False
        )
        memori.enable()

        print("Memori: Successfully initialized with full features")
        print("  - conscious_ingest: ON (AI memory analysis)")
        print("  - auto_ingest: ON (automatic context injection)")
        return memori

    except Exception as e:
        print(f"WARNING: Memori initialization failed: {e}")
        print("Continuing without Memori session memory...")
        return None

def inject_background_context_to_memori(memori, background_db):
    """
    Inject all saved backgrounds into Memori's conscious memory.

    This ensures Memori is always aware of finalized backgrounds
    saved in the SQLite database.
    """
    saved_backgrounds = background_db.get_all_backgrounds()

    if saved_backgrounds:
        # Build context string from all saved backgrounds
        context_parts = ["=== FINALIZED BACKGROUNDS IN DATABASE ===\n"]

        for bg in saved_backgrounds:
            context_parts.append(f"\n--- Background ID: {bg['id']} ---")
            context_parts.append(f"Title: {bg['title']}")
            context_parts.append(f"Created: {bg['created_at']}")
            context_parts.append(f"Query: {bg['query']}\n")
            context_parts.append("BACKGROUND CONTENT:")

            for para_num, para_text in bg['paragraphs']:
                context_parts.append(f"{para_num} {para_text}")

            context_parts.append("\n" + "="*50 + "\n")

        background_context = "\n".join(context_parts)

        # Store in session state for injection into prompts
        return background_context
    else:
        return None

@st.cache_resource
def initialize_settings():
    # os.environ["NVIDIA_API_KEY"] = "" #set API key here (for embeddings)
    # os.environ["ANTHROPIC_API_KEY"] = "" #set Claude API key here (for LLM)
    # Use llama-3.2-nv-embedqa-1b-v2 (outputs 2048 dimensions by default)
    Settings.embed_model = NVIDIAEmbedding(
        model="nvidia/llama-3.2-nv-embedqa-1b-v2",
        truncate="END"
    )
    Settings.llm = initialize_llm()
    # Use TokenTextSplitter instead of SentenceSplitter to avoid NLTK/sqlite3 dependency
    from llama_index.core.node_parser import TokenTextSplitter
    Settings.text_splitter = TokenTextSplitter(chunk_size=600, chunk_overlap=50)

# Create index from documents (using Pinecone vector store with namespaces)
def create_index(documents, pinecone_index, namespace="general-docs"):
    """
    Create vector index using Pinecone with namespace support.

    Args:
        documents: List of documents to index
        pinecone_index: Pinecone index instance
        namespace: Namespace to separate different types of content
                  "general-docs" - PPTX, general DOCX, invention details
                  "patent-claims" - Patent claims only
    """
    try:
        # Create Pinecone vector store with namespace
        vector_store = PineconeVectorStore(
            pinecone_index=pinecone_index,
            namespace=namespace
        )

        # Create storage context
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # Create index from documents
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context
        )

        print(f"Successfully indexed {len(documents)} documents in Pinecone namespace '{namespace}'")
        return index

    except Exception as e:
        print(f"Error creating index: {e}")
        raise

# ============================================================================
# TAB MANAGEMENT HELPER FUNCTIONS
# ============================================================================

def unlock_next_tab(current_tab_name):
    """Unlock the next tab after completing current tab."""
    tab_order = [
        'background', 'summary', 'drawings',
        'technical_problems', 'technical_advantages',
        'summary_paraphrase', 'figure2_intro',
        'sequencing', 'figure2_enablement', 'scenario_diagrams'
    ]

    try:
        current_index = tab_order.index(current_tab_name)
        if current_index < len(tab_order) - 1:
            next_tab = tab_order[current_index + 1]
            st.session_state['tabs_unlocked'][next_tab] = True
            return next_tab
    except ValueError:
        pass
    return None

def get_cumulative_context(retriever, query):
    """
    Get cumulative context from all sources for section generation.

    Returns:
        dict with 'pinecone_context', 'previous_sections', 'patent_info'
    """
    # 1. Retrieve from Pinecone (general-docs namespace)
    retrieved_nodes = retriever.retrieve(query)
    context_parts = []
    for idx, node in enumerate(retrieved_nodes):
        context_parts.append(f"Document {idx+1}:\n{node.text}\n")
    pinecone_context = "\n".join(context_parts) if context_parts else "No relevant documents found."

    # 2. Get all previously saved sections
    previous_sections = st.session_state['patent_sections_db'].get_all_sections_context()

    # 3. Get patent information
    patent_title = st.session_state.get('title_of_invention', '')
    patent_claims = st.session_state['patent_db'].get_all_claims() if st.session_state['patent_db'] else []

    patent_info = ""
    if patent_title:
        patent_info += f"Patent Title: {patent_title}\n\n"
    if patent_claims:
        patent_info += f"Patent Claims ({len(patent_claims)} claims):\n"
        for claim_num, claim_text in patent_claims[:3]:  # Show first 3 claims
            patent_info += f"Claim {claim_num}: {claim_text[:200]}...\n"

    return {
        'pinecone_context': pinecone_context,
        'previous_sections': previous_sections,
        'patent_info': patent_info
    }

def generate_section_content(section_type, system_prompt, query, retriever):
    """
    Generate content for any patent section using cumulative context.

    IMPORTANT: This function maintains antecedent basis across all sections.
    Terms introduced in earlier sections will be properly referenced with "the" in later sections.

    Args:
        section_type: 'background', 'summary', etc.
        system_prompt: Custom system prompt for this section
        query: User's query/instructions
        retriever: Pinecone retriever instance

    Returns:
        Generated content string
    """
    # Get cumulative context from vector DB
    context = get_cumulative_context(retriever, query)

    # Get title for context
    title_of_invention = st.session_state.get('title_of_invention', 'Patent Application')

    # Use Patent Context Manager for antecedent basis tracking
    context_manager = st.session_state.get('patent_context_manager')

    if context_manager:
        # Build enhanced system prompt with FULL session context for antecedent basis
        session_context = context_manager.get_section_specific_context(
            section_type,
            title_of_invention
        )

        # Combine: Session context (antecedent basis) + Admin prompt
        enhanced_system_prompt = f"""{session_context}

{"=" * 60}
**ADMIN-CONFIGURED GENERATION INSTRUCTIONS:**
{"=" * 60}

{system_prompt}"""
    else:
        # Fallback if context manager not available
        enhanced_system_prompt = system_prompt

        if context['previous_sections']:
            enhanced_system_prompt += f"\n\n{context['previous_sections']}\n\nYou are aware of all previously completed sections listed above. This is part of the ongoing patent document generation session."

        if context['patent_info']:
            enhanced_system_prompt += f"\n\n{context['patent_info']}"

    # Build user message
    user_message = f"""SESSION CONTEXT:
This is part of an ongoing patent document generation session for the "{section_type.upper()}" section.

**TITLE OF INVENTION:** {title_of_invention}

You have access to:
1. ALL previously completed sections (for antecedent basis - use "the" for previously introduced terms)
2. Retrieved document context (from vector database)
3. Patent claims and title

**ANTECEDENT BASIS REMINDER:**
- If a term was introduced in ANY previous section, use "the" before it
- Example: If "processing unit" was introduced earlier, write "the processing unit" now

RETRIEVED CONTEXT FROM DOCUMENTS:
{context['pinecone_context']}

USER QUERY FOR THIS SECTION:
{query}

Please generate comprehensive content for the {section_type.upper()} section.
ENSURE antecedent basis compliance - use "the" for all previously introduced terms."""

    # Call Claude API (Memori intercepts)
    response = st.session_state['anthropic_client'].messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=enhanced_system_prompt,
        messages=[{
            "role": "user",
            "content": user_message
        }]
    )

    return response.content[0].text

def save_section_and_notify_memori(section_type, title, query, content, skipped=False):
    """
    Save section to database and notify context manager for antecedent basis tracking.

    This function:
    1. Saves the section to SQLite database
    2. Registers the completion with Patent Context Manager (for antecedent basis)
    3. Notifies Memori for session awareness

    Returns:
        section_id
    """
    # Save to unified database
    section_id = st.session_state['patent_sections_db'].save_section(
        section_type=section_type,
        title=title,
        query=query,
        content=content,
        skipped=skipped
    )

    # Register with Patent Context Manager for antecedent basis tracking
    context_manager = st.session_state.get('patent_context_manager')
    if context_manager and not skipped:
        context_manager.register_section_completion(section_type, content)

    # Notify Memori
    if st.session_state.get('anthropic_client') and not skipped:
        session_event = f"""
SESSION EVENT: {section_type.upper()} Section {'Skipped' if skipped else 'Saved'}

Section ID: {section_id}
Section Type: {section_type}
Title: {title}
{'Content: (Skipped)' if skipped else f'Query: {query[:100]}...'}

ANTECEDENT BASIS UPDATE:
All terms introduced in this section are now ESTABLISHED.
Future sections MUST use "the" before referencing any of these terms.

This section is now part of the finalized patent document session memory.
All future interactions should be aware of this completed section.
"""
        try:
            st.session_state['anthropic_client'].messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=100,
                system="You are a session memory manager tracking patent document progress and antecedent basis. Acknowledge this event briefly.",
                messages=[{
                    "role": "user",
                    "content": session_event
                }]
            )
        except:
            pass  # Continue without notification

    return section_id

def display_system_prompt(section_key, title="System Prompt"):
    """Display a non-editable system prompt from admin configuration.

    Args:
        section_key: The key for the prompt in admin_config_db
        title: Display title for the prompt section

    Returns:
        The prompt text for use in generation
    """
    prompt_text = st.session_state['admin_config_db'].get_prompt(section_key)

    if prompt_text:
        with st.expander(f"📋 {title} (configured by admin)", expanded=False):
            st.markdown("*This prompt is configured by the administrator and cannot be edited by users.*")
            st.text_area(
                "System Prompt",
                value=prompt_text,
                height=200,
                disabled=True,
                key=f"display_prompt_{section_key}_{id(prompt_text)}"
            )

    return prompt_text

def get_system_prompt(section_key):
    """Get system prompt from admin configuration.

    Args:
        section_key: The key for the prompt in admin_config_db

    Returns:
        The prompt text or a default message if not found
    """
    prompt_text = st.session_state['admin_config_db'].get_prompt(section_key)
    return prompt_text if prompt_text else "System prompt not configured. Please contact administrator."

def main():
    initialize_settings()
    llm = initialize_llm()

    # Initialize Patent Claims Database
    if st.session_state['patent_db'] is None:
        st.session_state['patent_db'] = PatentClaimsDatabase()

    # Initialize Background Database
    if st.session_state['background_db'] is None:
        st.session_state['background_db'] = BackgroundDatabase()

    # Initialize Patent Sections Database (unified for all sections)
    if st.session_state['patent_sections_db'] is None:
        st.session_state['patent_sections_db'] = PatentSectionsDatabase()

    # Initialize Patent Context Manager (for antecedent basis tracking)
    if st.session_state['patent_context_manager'] is None:
        st.session_state['patent_context_manager'] = PatentContextManager(
            st.session_state['patent_sections_db'],
            st.session_state['patent_db']
        )

    # Initialize Pinecone
    if not st.session_state['pinecone_initialized']:
        try:
            pinecone_index = initialize_pinecone()
            st.session_state['pinecone_index'] = pinecone_index
            st.session_state['pinecone_initialized'] = True
            st.sidebar.success("✅ Pinecone vector database connected!")
        except Exception as e:
            st.sidebar.error(f"❌ Pinecone initialization failed: {e}\nPlease check your PINECONE_API_KEY.")
            return

    # Initialize Memori for conversation memory
    if not st.session_state['memori_initialized']:
        try:
            memori = initialize_memori()
            # Create Anthropic client for direct API calls (Memori intercepts these)
            st.session_state['anthropic_client'] = AnthropicClient(api_key=os.getenv("ANTHROPIC_API_KEY"))
            st.session_state['memori_initialized'] = True
            st.sidebar.success("✅ Memori enabled - conversations will be remembered across sessions!")
        except Exception as e:
            st.sidebar.warning(f"⚠️ Memori initialization failed: {e}\nContinuing without persistent memory.")
            st.session_state['anthropic_client'] = AnthropicClient(api_key=os.getenv("ANTHROPIC_API_KEY"))

    col1, col2 = st.columns([1, 2])

    with col1:
        st.title("Multimodal RAG")

        # Display Title of Invention if extracted
        if st.session_state.get('title_of_invention'):
            st.text_input(
                "Title of Invention",
                value=st.session_state['title_of_invention'],
                disabled=True,
                key="title_display"
            )

        # Add Context Awareness info
        with st.expander("🧠 Context & Antecedent Basis Tracking"):
            context_manager = st.session_state.get('patent_context_manager')
            if context_manager:
                context_summary = context_manager.get_context_summary()
                st.markdown("""
                **Antecedent Basis Tracking is ACTIVE**

                This ensures patent drafting consistency:
                - First mention of a term: "application containers"
                - All subsequent mentions: "**the** application containers"
                """)

                # Show completed sections
                if context_summary['sections_completed']:
                    st.markdown("**Sections Completed (context available):**")
                    for section in context_summary['sections_completed']:
                        st.markdown(f"- ✅ {section.replace('_', ' ').title()}")
                else:
                    st.markdown("*No sections completed yet*")

                st.markdown(f"**Claims Available:** {context_summary['claims_available']}")
            else:
                st.warning("Context manager not initialized")

            st.markdown("---")
            st.markdown("""
            **Memori is enabled** - Your conversations are intelligently remembered:
            - **Conscious Mode**: Background agent analyzes and promotes important memories
            - **Auto Mode**: Dynamically retrieves relevant context per query
            - **Persistent Storage**: SQLite database stores all conversations
            - **Cross-Session**: Context preserved between sessions

            Memory database: `multimodal_rag_memory.db`
            """)

        st.subheader("Upload Documents")

        # Input Document 1: PowerPoint (Optional)
        st.markdown("**Input Document 1** (Optional - PPTX)")
        input_doc1 = st.file_uploader(
            "Upload PowerPoint presentation",
            type=['pptx', 'ppt'],
            key="input_doc1",
            help="Optional: PowerPoint presentation for knowledge base"
        )

        # Input Document 2: Patent Claims Word Document (Optional - Special Processing)
        st.markdown("**Input Document 2** (Optional - Patent Claims DOCX)")
        input_doc2 = st.file_uploader(
            "Upload Patent Claims Document",
            type=['docx', 'doc'],
            key="input_doc2",
            help="Optional: Word document with patent claims. Title and claims will be extracted and stored separately."
        )

        # Auto-extract title when Document 2 is uploaded
        if input_doc2 is not None and st.session_state['title_of_invention'] is None:
            try:
                from utils import save_uploaded_file
                from patent_processor import extract_title_of_invention

                # Save and extract title
                with st.spinner("Extracting title of invention..."):
                    docx_path = save_uploaded_file(input_doc2)
                    title = extract_title_of_invention(docx_path)
                    st.session_state['title_of_invention'] = title
                    st.success(f"✅ Title extracted: {title}")
            except Exception as e:
                st.error(f"Error extracting title: {e}")

        # Input Document 3: Word Document (Optional)
        st.markdown("**Input Document 3** (Optional - DOCX)")
        input_doc3 = st.file_uploader(
            "Upload Word document",
            type=['docx', 'doc'],
            key="input_doc3",
            help="Optional: Additional Word document for knowledge base"
        )

        # Process Documents Button
        if st.button("Process Documents", type="primary"):
            all_documents = []

            # Check if at least one document is uploaded
            if not any([input_doc1, input_doc2, input_doc3]):
                st.error("⚠️ Please upload at least one document")
            else:
                with st.spinner("Processing documents..."):
                    patent_claims_docs = []  # Separate list for patent claims

                    # Process Input Document 1 (PPTX)
                    if input_doc1:
                        st.info(f"Processing Input Document 1: {input_doc1.name}")
                        try:
                            docs = load_multimodal_data([input_doc1], llm)
                            all_documents.extend(docs)
                            st.success(f"✅ Document 1 processed: {len(docs)} elements extracted")
                        except Exception as e:
                            st.error(f"❌ Error processing Document 1: {e}")

                    # Process Input Document 2 (Patent Claims - Special Processing)
                    if input_doc2:
                        st.info(f"Processing Input Document 2 (Patent Claims): {input_doc2.name}")
                        try:
                            # Save file content to avoid stream consumption issues
                            temp_dir = os.path.join(os.getcwd(), "vectorstore", "ppt_references", "tmp")
                            os.makedirs(temp_dir, exist_ok=True)
                            docx_path = os.path.join(temp_dir, input_doc2.name)

                            with open(docx_path, "wb") as temp_file:
                                temp_file.write(input_doc2.getvalue())

                            # Extract and save title + claims to SQLite
                            result = process_patent_document(docx_path, st.session_state['patent_db'])

                            if result['success']:
                                st.success(f"✅ Patent Document processed:")
                                st.write(f"  - **Title**: {result['title']}")
                                st.write(f"  - **Claims**: {result['num_claims']} claims extracted")
                                st.write(f"  - **Storage**: Saved to SQLite database (patent_claims.db)")
                                st.session_state['patent_processed'] = True

                                # Add patent claims to BOTH namespaces
                                from document_processors import process_docx_file
                                docs = process_docx_file(docx_path, llm)

                                # Add to general-docs namespace (for background generation)
                                all_documents.extend(docs)

                                # Also keep in separate list for patent-claims namespace
                                patent_claims_docs.extend(docs)

                                st.info(f"📌 Patent claims will be stored in BOTH 'general-docs' and 'patent-claims' namespaces")
                            else:
                                st.error(f"❌ Error processing patent claims: {result.get('error')}")

                        except Exception as e:
                            st.error(f"❌ Error processing Document 2: {e}")
                            import traceback
                            traceback.print_exc()

                    # Process Input Document 3 (DOCX)
                    if input_doc3:
                        st.info(f"Processing Input Document 3: {input_doc3.name}")
                        try:
                            docs = load_multimodal_data([input_doc3], llm)
                            all_documents.extend(docs)
                            st.success(f"✅ Document 3 processed: {len(docs)} elements extracted")
                        except Exception as e:
                            st.error(f"❌ Error processing Document 3: {e}")

                    # Index general documents in Pinecone (namespace: "general-docs")
                    if all_documents:
                        st.info(f"Indexing {len(all_documents)} general documents in Pinecone namespace 'general-docs'...")
                        st.session_state['index'] = create_index(
                            all_documents,
                            st.session_state['pinecone_index'],
                            namespace="general-docs"
                        )
                        st.success(f"✅ General documents indexed successfully!")

                    # Index patent claims in SEPARATE namespace (namespace: "patent-claims")
                    if patent_claims_docs:
                        st.info(f"Indexing {len(patent_claims_docs)} patent claims in SEPARATE Pinecone namespace 'patent-claims'...")
                        st.session_state['claims_index'] = create_index(
                            patent_claims_docs,
                            st.session_state['pinecone_index'],
                            namespace="patent-claims"
                        )
                        st.success(f"✅ Patent claims indexed in separate namespace!")

                    if not all_documents and not patent_claims_docs:
                        st.warning("⚠️ No documents were extracted for indexing")

        # Show patent info if processed
        if st.session_state['patent_processed']:
            with st.expander("📄 Patent Information"):
                title = st.session_state['patent_db'].get_title()
                claims = st.session_state['patent_db'].get_all_claims()

                if title:
                    st.markdown(f"**Title of Invention:**")
                    st.write(title)

                if claims:
                    st.markdown(f"**Number of Claims:** {len(claims)}")
                    if st.checkbox("Show all claims"):
                        for claim_num, claim_text in claims:
                            st.markdown(f"**Claim {claim_num}:**")
                            st.text(claim_text)
                            st.markdown("---")

        # Keep the directory upload option
        st.markdown("---")
        st.subheader("Or Upload from Directory")
        use_directory = st.checkbox("Use directory path instead")

        if use_directory:
            directory_path = st.text_input("Enter directory path:")
            if directory_path and st.button("Process Directory"):
                if os.path.isdir(directory_path):
                    with st.spinner("Processing directory..."):
                        documents = load_data_from_directory(directory_path, llm)
                        if len(documents) == 0:
                            st.error("⚠️ No documents were extracted from the directory! Check the terminal/console for detailed error messages.")
                        else:
                            st.session_state['index'] = create_index(documents, st.session_state['pinecone_index'])
                            st.success(f"✅ Directory processed successfully! {len(documents)} documents indexed in Pinecone and ready for questions.")
                else:
                    st.error("Invalid directory path. Please enter a valid path.")

    with col2:
        if st.session_state['index'] is not None:
            # Get retriever for all tabs
            retriever = st.session_state['index'].as_retriever(similarity_top_k=5)

            # Create 10-tab interface
            tab_names = [
                "1️⃣ BACKGROUND",
                "2️⃣ SUMMARY",
                "3️⃣ BRIEF DESCRIPTION OF DRAWINGS",
                "4️⃣ TECHNICAL PROBLEMS",
                "5️⃣ TECHNICAL ADVANTAGES",
                "6️⃣ SUMMARY PARAPHRASE",
                "7️⃣ FIGURE 2 INTRODUCTION",
                "8️⃣ SEQUENCING",
                "9️⃣ FIGURE 2 CLAIM ENABLEMENT",
                "🔟 SCENARIO DIAGRAMS"
            ]

            tabs = st.tabs(tab_names)

            # ================================================================
            # TAB 0: BACKGROUND (Always unlocked, required to proceed)
            # ================================================================
            with tabs[0]:
                st.markdown("### Background Section")

                section_type = 'background'
                section_key = f'{section_type}_output'

                # System Prompt (Admin Configured - Non-editable)
                system_prompt = display_system_prompt('background', "Background Section Prompt")

                # Query Input
                query = st.text_area(
                    "Query Input",
                    placeholder="Enter your query to generate background context...",
                    height=100,
                    key=f"{section_type}_query",
                    help="Ask a question or provide context"
                )

                # Generate Button
                if st.button("Generate Background", type="primary", key=f"{section_type}_generate"):
                    if not query:
                        st.error("⚠️ Please enter a query")
                    else:
                        with st.spinner("Generating background..."):
                            try:
                                output = generate_section_content(section_type, system_prompt, query, retriever)
                                st.session_state['current_section_output'][section_key] = {
                                    "query": query,
                                    "output": output
                                }
                                st.success("✅ Background generated successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")

                # Display Generated Content
                if section_key in st.session_state['current_section_output']:
                    st.markdown("---")
                    st.markdown("### Generated Background")
                    st.markdown(st.session_state['current_section_output'][section_key]['output'])

                    # Save and Proceed Buttons
                    col_save, col_proceed = st.columns(2)

                    with col_save:
                        if st.button("💾 Save Background", type="primary", key=f"{section_type}_save"):
                            title = st.session_state.get('title_of_invention', 'Background Section')
                            query_text = st.session_state['current_section_output'][section_key]['query']
                            content = st.session_state['current_section_output'][section_key]['output']

                            try:
                                section_id = save_section_and_notify_memori(section_type, title, query_text, content)
                                st.success(f"✅ Background saved! (ID: {section_id})")
                                st.balloons()
                            except Exception as e:
                                st.error(f"❌ Error saving: {str(e)}")

                    with col_proceed:
                        # Check if background is saved
                        bg_saved = st.session_state['patent_sections_db'].get_section('background') is not None

                        if bg_saved:
                            if st.button("➡️ Proceed to Summary", key=f"{section_type}_proceed"):
                                unlock_next_tab('background')
                                st.session_state['current_section_output'].pop(section_key, None)
                                st.success("✅ Summary tab unlocked!")
                                st.rerun()
                        else:
                            st.info("💾 Save background first to proceed")

                # Show Saved Background
                saved_bg = st.session_state['patent_sections_db'].get_section('background')
                if saved_bg and not saved_bg['skipped']:
                    st.markdown("---")
                    st.markdown("### Saved Background")
                    with st.expander(f"View Saved Background (ID: {saved_bg['id']})"):
                        for para_num, para_text in saved_bg['paragraphs']:
                            st.markdown(f"**{para_num}** {para_text}\n")

            # ================================================================
            # TAB 1: SUMMARY (Specialized - 3 Paragraphs)
            # ================================================================
            with tabs[1]:
                if not st.session_state['tabs_unlocked']['summary']:
                    st.warning("⚠️ Complete Background section first to unlock this tab")
                else:
                    st.markdown("### Summary Section (3 Paragraphs)")
                    st.info("This section generates 3 paragraphs: [0003] paraphrased claim, [0004] and [0005] standard text")

                    section_type = 'summary'
                    section_key = f'{section_type}_output'

                    # Step 1: Display Independent Claim
                    st.markdown("#### Step 1: Independent Claim (from database)")
                    independent_claim = st.session_state['patent_db'].get_independent_claim()

                    if independent_claim:
                        st.text_area(
                            "Independent Claim (Claim 1)",
                            value=independent_claim,
                            height=200,
                            disabled=True,
                            key="summary_independent_claim_display"
                        )
                    else:
                        st.warning("⚠️ No independent claim found. Please upload Patent Claims document first.")

                    # Step 2: Generate Paraphrased Summary
                    st.markdown("#### Step 2: Generate Paraphrased Summary [0003]")

                    # Display admin-configured prompt (non-editable)
                    summary_system_prompt = display_system_prompt('summary', "Summary Section Prompt")

                    if st.button("Generate Summary Paragraphs", type="primary", key="summary_generate"):
                        if not independent_claim:
                            st.error("⚠️ Cannot generate summary without independent claim")
                        else:
                            with st.spinner("Generating paraphrased summary..."):
                                try:
                                    # Get title from database
                                    title = st.session_state.get('title_of_invention', 'Title not found')

                                    # Get admin-configured prompt
                                    paraphrase_template = get_system_prompt('summary')

                                    # Call Claude API with paraphrasing template
                                    response = st.session_state['anthropic_client'].messages.create(
                                        model="claude-sonnet-4-20250514",
                                        max_tokens=2048,
                                        system=paraphrase_template,
                                        messages=[{
                                            "role": "user",
                                            "content": f"""Title of Invention: {title}

Independent Claim to Paraphrase:
{independent_claim}

Please generate the paraphrased summary paragraph [0003] following all the rules."""
                                        }]
                                    )

                                    para_0003 = response.content[0].text.strip()

                                    # Fixed paragraphs [0004] and [0005]
                                    para_0004 = "Further aspects of the present disclosure are directed to systems and computer program products containing functionality consistent with the method described above."
                                    para_0005 = "Additional technical features and benefits are realized through the techniques of the disclosure. Embodiments and aspects of the disclosure are described in detail herein and are considered a part of the claimed subject matter. For a better understanding, refer to the detailed description and the drawings."

                                    # Combine all 3 paragraphs
                                    full_summary = f"[0003] {para_0003}\n\n[0004] {para_0004}\n\n[0005] {para_0005}"

                                    # Store in session state
                                    st.session_state['current_section_output'][section_key] = {
                                        "query": "Generated from independent claim paraphrasing",
                                        "output": full_summary,
                                        "para_0003": para_0003,
                                        "para_0004": para_0004,
                                        "para_0005": para_0005
                                    }

                                    st.success("✅ Summary paragraphs generated!")
                                    st.rerun()

                                except Exception as e:
                                    st.error(f"Error generating summary: {str(e)}")

                    # Display Generated Summary
                    if section_key in st.session_state['current_section_output']:
                        st.markdown("---")
                        st.markdown("### Generated Summary (3 Paragraphs)")

                        # Display each paragraph separately
                        st.markdown(f"**[0003]** {st.session_state['current_section_output'][section_key]['para_0003']}\n")
                        st.markdown(f"**[0004]** {st.session_state['current_section_output'][section_key]['para_0004']}\n")
                        st.markdown(f"**[0005]** {st.session_state['current_section_output'][section_key]['para_0005']}\n")

                        # Save, Skip, Proceed Buttons
                        col_save, col_skip, col_proceed = st.columns(3)

                        with col_save:
                            if st.button("💾 Save Summary", type="primary", key="summary_save"):
                                title = st.session_state.get('title_of_invention', 'Summary Section')
                                query_text = st.session_state['current_section_output'][section_key]['query']
                                content = st.session_state['current_section_output'][section_key]['output']

                                try:
                                    section_id = save_section_and_notify_memori(section_type, title, query_text, content)
                                    st.success(f"✅ Summary saved! (ID: {section_id})")
                                    st.balloons()
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")

                        with col_skip:
                            if st.button("⏭️ Skip (Complete Later)", key="summary_skip"):
                                title = st.session_state.get('title_of_invention', 'Summary Section')
                                save_section_and_notify_memori(section_type, title, "", "", skipped=True)
                                unlock_next_tab('summary')
                                st.session_state['current_section_output'].pop(section_key, None)
                                st.info("⏭️ Summary skipped. You can complete it later. Drawings tab unlocked!")
                                st.rerun()

                        with col_proceed:
                            summary_saved = st.session_state['patent_sections_db'].get_section('summary') is not None

                            if summary_saved:
                                if st.button("➡️ Proceed to Drawings", key="summary_proceed"):
                                    unlock_next_tab('summary')
                                    st.session_state['current_section_output'].pop(section_key, None)
                                    st.success("✅ Drawings tab unlocked!")
                                    st.rerun()
                            else:
                                st.info("💾 Save or Skip first to proceed")

                    # Show Saved Summary
                    saved_section = st.session_state['patent_sections_db'].get_section('summary')
                    if saved_section:
                        st.markdown("---")
                        if saved_section['skipped']:
                            st.markdown("### ⏭️ Summary Section (Skipped - Complete Later)")
                        else:
                            st.markdown("### Saved Summary")
                            with st.expander(f"View Saved Summary (ID: {saved_section['id']})"):
                                for para_num, para_text in saved_section['paragraphs']:
                                    st.markdown(f"**{para_num}** {para_text}\n")

            # ================================================================
            # TAB 2: BRIEF DESCRIPTION OF DRAWINGS (Dynamic FIG Generation)
            # ================================================================
            with tabs[2]:
                if not st.session_state['tabs_unlocked']['drawings']:
                    st.warning("⚠️ Complete Summary section first to unlock this tab")
                else:
                    st.markdown("### Brief Description of Drawings")
                    st.info("Specify the number of scenario diagrams to generate dynamic FIG paragraphs")

                    section_type = 'drawings'
                    section_key = f'{section_type}_output'
                    scenario_key = 'scenario_diagram_count'

                    # Display admin-configured prompt (non-editable)
                    drawings_system_prompt = display_system_prompt('drawings', "Drawings Section Prompt")

                    # Step 1: Ask for number of scenario diagrams
                    st.markdown("#### Step 1: Specify Number of Scenario Diagrams")

                    scenario_count = st.number_input(
                        "How many scenario diagrams do you have?",
                        min_value=1,
                        max_value=10,
                        value=st.session_state.get(scenario_key, 3),
                        step=1,
                        key="drawings_scenario_count_input"
                    )

                    # Store scenario count in session state
                    st.session_state[scenario_key] = scenario_count

                    st.markdown("#### Step 2: Generate Figure Descriptions")

                    # Generate button
                    if st.button("Generate Figure Descriptions", type="primary", key="drawings_generate"):
                        with st.spinner("Generating figure descriptions..."):
                            try:
                                # Get title from database
                                title = st.session_state.get('title_of_invention', 'Title not found')

                                # Build the drawing descriptions
                                paragraphs = []
                                para_num = 6  # Starting paragraph number

                                # [0006] - Fixed intro
                                paragraphs.append(f"[{para_num:04d}] The following description will provide details of preferred embodiments with reference to the following figures, wherein:")
                                para_num += 1

                                # [0007] - FIG. 1
                                paragraphs.append(f"[{para_num:04d}] FIG. 1 is a diagram that illustrates a computing environment for {title}, in accordance with various embodiments of the disclosure;")
                                para_num += 1

                                # [0008] - FIG. 2
                                paragraphs.append(f"[{para_num:04d}] FIG. 2 is a diagram that illustrates an environment for {title}, in accordance with various embodiments of the disclosure;")
                                para_num += 1

                                # Dynamic scenario diagrams [0009] to [0008+X]
                                scenario_descriptions = []
                                for i in range(scenario_count):
                                    fig_num = 3 + i
                                    scenario_descriptions.append({
                                        'para_num': para_num,
                                        'fig_num': fig_num,
                                        'description': ''  # Blank field to fill
                                    })
                                    para_num += 1

                                # Store scenario descriptions for editing
                                st.session_state[f'{section_key}_scenarios'] = scenario_descriptions

                                # [X+9] - FIG. (2+X+1) - Flowchart 1
                                flowchart1_fig = 2 + scenario_count + 1
                                paragraphs.append(f"[{para_num:04d}] FIG. {flowchart1_fig} is a diagram that illustrates a flowchart of a set of operations for {title}, in accordance with an embodiment of the disclosure; and")
                                para_num += 1

                                # [X+10] - FIG. (2+X+2) - Flowchart 2
                                flowchart2_fig = 2 + scenario_count + 2
                                paragraphs.append(f"[{para_num:04d}] FIG. {flowchart2_fig} is a diagram that illustrates a flowchart of a set of operations for {title}, in accordance with an alternative embodiment of the disclosure.")

                                # Store in session state
                                st.session_state['current_section_output'][section_key] = {
                                    "query": f"Generated with {scenario_count} scenario diagrams",
                                    "paragraphs": paragraphs,
                                    "scenario_count": scenario_count,
                                    "scenario_descriptions": scenario_descriptions,
                                    "generated": True
                                }

                                st.success(f"✅ Figure descriptions generated for {scenario_count} scenario diagrams!")
                                st.rerun()

                            except Exception as e:
                                st.error(f"Error generating drawings: {str(e)}")

                    # Display and edit scenario descriptions
                    if section_key in st.session_state['current_section_output'] and st.session_state['current_section_output'][section_key].get('generated'):
                        st.markdown("---")
                        st.markdown("### Generated Figure Descriptions")

                        # Display fixed paragraphs
                        for para in st.session_state['current_section_output'][section_key]['paragraphs']:
                            st.markdown(para)

                        # Edit scenario diagram descriptions
                        st.markdown("---")
                        st.markdown("#### Fill in Scenario Diagram Descriptions")
                        st.info("Enter descriptions for each scenario diagram below:")

                        scenario_descriptions = st.session_state[f'{section_key}_scenarios']
                        updated_scenarios = []

                        for idx, scenario in enumerate(scenario_descriptions):
                            description = st.text_input(
                                f"FIG. {scenario['fig_num']} Description",
                                value=scenario['description'],
                                placeholder=f"Enter description for Figure {scenario['fig_num']}...",
                                key=f"scenario_fig_{scenario['fig_num']}_desc"
                            )
                            updated_scenarios.append({
                                'para_num': scenario['para_num'],
                                'fig_num': scenario['fig_num'],
                                'description': description
                            })

                        # Update session state with filled descriptions
                        st.session_state[f'{section_key}_scenarios'] = updated_scenarios

                        # Check if all scenarios are filled
                        all_filled = all(s['description'].strip() for s in updated_scenarios)

                        # Generate final output
                        if all_filled:
                            # Build complete output with scenario descriptions
                            title = st.session_state.get('title_of_invention', 'Title not found')
                            complete_output = []

                            para_num = 6
                            # [0006]
                            complete_output.append(f"[{para_num:04d}] The following description will provide details of preferred embodiments with reference to the following figures, wherein:")
                            para_num += 1

                            # [0007]
                            complete_output.append(f"[{para_num:04d}] FIG. 1 is a diagram that illustrates a computing environment for {title}, in accordance with various embodiments of the disclosure;")
                            para_num += 1

                            # [0008]
                            complete_output.append(f"[{para_num:04d}] FIG. 2 is a diagram that illustrates an environment for {title}, in accordance with various embodiments of the disclosure;")
                            para_num += 1

                            # Scenario diagrams
                            for scenario in updated_scenarios:
                                complete_output.append(f"[{scenario['para_num']:04d}] FIG. {scenario['fig_num']} is a diagram that illustrates {scenario['description']}, in accordance with an embodiment of the disclosure;")

                            # Flowcharts
                            flowchart1_fig = 2 + scenario_count + 1
                            complete_output.append(f"[{para_num:04d}] FIG. {flowchart1_fig} is a diagram that illustrates a flowchart of a set of operations for {title}, in accordance with an embodiment of the disclosure; and")
                            para_num += 1

                            flowchart2_fig = 2 + scenario_count + 2
                            complete_output.append(f"[{para_num:04d}] FIG. {flowchart2_fig} is a diagram that illustrates a flowchart of a set of operations for {title}, in accordance with an alternative embodiment of the disclosure.")

                            final_output = "\n\n".join(complete_output)

                            # Store complete output
                            st.session_state['current_section_output'][section_key]['output'] = final_output
                            st.session_state['current_section_output'][section_key]['complete'] = True

                            st.markdown("---")
                            st.markdown("### Complete Drawings Section")
                            st.text_area("Final Output", value=final_output, height=400, disabled=True, key="drawings_final_output")

                        else:
                            st.warning("⚠️ Please fill in all scenario diagram descriptions before saving")

                        # Save, Skip, Proceed Buttons
                        col_save, col_skip, col_proceed = st.columns(3)

                        with col_save:
                            if all_filled:
                                if st.button("💾 Save Drawings", type="primary", key="drawings_save"):
                                    title = st.session_state.get('title_of_invention', 'Drawings Section')
                                    query_text = st.session_state['current_section_output'][section_key]['query']
                                    content = st.session_state['current_section_output'][section_key]['output']

                                    try:
                                        section_id = save_section_and_notify_memori(section_type, title, query_text, content)
                                        st.success(f"✅ Drawings saved! (ID: {section_id})")
                                        st.balloons()
                                    except Exception as e:
                                        st.error(f"❌ Error: {str(e)}")
                            else:
                                st.button("💾 Save Drawings", type="primary", disabled=True, key="drawings_save_disabled")

                        with col_skip:
                            if st.button("⏭️ Skip (Complete Later)", key="drawings_skip"):
                                save_section_and_notify_memori(section_type, "", "", "", skipped=True)
                                unlock_next_tab('drawings')
                                st.session_state['current_section_output'].pop(section_key, None)
                                st.info("⏭️ Drawings skipped. You can complete it later. Technical Problems tab unlocked!")
                                st.rerun()

                        with col_proceed:
                            drawings_saved = st.session_state['patent_sections_db'].get_section('drawings') is not None

                            if drawings_saved:
                                if st.button("➡️ Proceed to Technical Problems", key="drawings_proceed"):
                                    unlock_next_tab('drawings')
                                    st.session_state['current_section_output'].pop(section_key, None)
                                    st.success("✅ Technical Problems tab unlocked!")
                                    st.rerun()
                            else:
                                st.info("💾 Save or Skip first to proceed")

                    # Show Saved Drawings
                    saved_section = st.session_state['patent_sections_db'].get_section('drawings')
                    if saved_section:
                        st.markdown("---")
                        if saved_section['skipped']:
                            st.markdown("### ⏭️ Drawings Section (Skipped - Complete Later)")
                        else:
                            st.markdown("### Saved Drawings")
                            with st.expander(f"View Saved Drawings (ID: {saved_section['id']})"):
                                for para_num, para_text in saved_section['paragraphs']:
                                    st.markdown(f"**{para_num}** {para_text}\n")

            # ================================================================
            # TAB 3: TECHNICAL PROBLEMS (Cannot skip)
            # ================================================================
            with tabs[3]:
                if not st.session_state['tabs_unlocked']['technical_problems']:
                    st.warning("⚠️ Complete Drawings section first")
                else:
                    section_type = 'technical_problems'
                    section_key = f'{section_type}_output'
                    st.markdown("### Technical Problems")

                    # Display admin-configured prompt (non-editable)
                    system_prompt = display_system_prompt('technical_problems', "Technical Problems Prompt")
                    query = st.text_area("Query Input", placeholder="Describe the technical problems...", height=100, key=f"{section_type}_query")

                    if st.button("Generate", type="primary", key=f"{section_type}_generate"):
                        if query:
                            with st.spinner("Generating..."):
                                try:
                                    output = generate_section_content(section_type, system_prompt, query, retriever)
                                    st.session_state['current_section_output'][section_key] = {"query": query, "output": output}
                                    st.success("✅ Generated!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")

                    if section_key in st.session_state['current_section_output']:
                        st.markdown("---")
                        st.markdown(st.session_state['current_section_output'][section_key]['output'])

                        col_save, col_proceed = st.columns(2)
                        with col_save:
                            if st.button("💾 Save", type="primary", key=f"{section_type}_save"):
                                title = st.session_state.get('title_of_invention', '')
                                save_section_and_notify_memori(section_type, title, st.session_state['current_section_output'][section_key]['query'], st.session_state['current_section_output'][section_key]['output'])
                                st.success("✅ Saved!")

                        with col_proceed:
                            if st.session_state['patent_sections_db'].get_section('technical_problems'):
                                if st.button("➡️ Proceed", key=f"{section_type}_proceed"):
                                    unlock_next_tab('technical_problems')
                                    st.session_state['current_section_output'].pop(section_key, None)
                                    st.rerun()

                    saved_section = st.session_state['patent_sections_db'].get_section('technical_problems')
                    if saved_section:
                        st.markdown("---")
                        st.markdown("### Saved Technical Problems")
                        with st.expander(f"View Saved (ID: {saved_section['id']})"):
                            for para_num, para_text in saved_section['paragraphs']:
                                st.markdown(f"**{para_num}** {para_text}\n")

            # ================================================================
            # TAB 4: TECHNICAL ADVANTAGES (Cannot skip)
            # ================================================================
            # TAB 4: TECHNICAL ADVANTAGES (With Frontend Validation)
            # ================================================================
            with tabs[4]:
                if not st.session_state['tabs_unlocked']['technical_advantages']:
                    st.warning("⚠️ Complete Technical Problems section first")
                else:
                    section_type = 'technical_advantages'
                    section_key = f'{section_type}_output'
                    st.markdown("### Technical Advantages")

                    # FRONTEND VALIDATION - Show context loading status
                    st.markdown("#### Context Validation")

                    validation_col1, validation_col2, validation_col3 = st.columns(3)

                    # INPUT(I): Validate Technical Problems loaded from SQLite
                    with validation_col1:
                        tech_problems = st.session_state['patent_sections_db'].get_section('technical_problems')
                        if tech_problems and not tech_problems['skipped']:
                            st.success("✅ INPUT(I): Technical Problems loaded from SQLite")
                        else:
                            st.error("❌ INPUT(I): Technical Problems not found")

                    # INPUT(II): Validate context from general-docs namespace
                    with validation_col2:
                        if st.session_state['index'] is not None:
                            st.success("✅ INPUT(II): Context from 'general-docs' fetched")
                        else:
                            st.error("❌ INPUT(II): Vector database not loaded")

                    # INPUT(III): Validate claims from patent-claims namespace
                    with validation_col3:
                        claims = st.session_state['patent_db'].get_all_claims()
                        if claims:
                            st.success(f"✅ INPUT(III): {len(claims)} Claims loaded")
                        else:
                            st.error("❌ INPUT(III): Claims not found")

                    st.markdown("---")

                    # Display admin-configured prompt (non-editable)
                    system_prompt = display_system_prompt('technical_advantages', "Technical Advantages Prompt")
                    query = st.text_area("Query Input", placeholder="Describe the technical advantages in context of the problems...", height=100, key=f"{section_type}_query")

                    if st.button("Generate", type="primary", key=f"{section_type}_generate"):
                        if query:
                            with st.spinner("Generating..."):
                                try:
                                    output = generate_section_content(section_type, system_prompt, query, retriever)
                                    st.session_state['current_section_output'][section_key] = {"query": query, "output": output}
                                    st.success("✅ Generated!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")

                    if section_key in st.session_state['current_section_output']:
                        st.markdown("---")
                        st.markdown(st.session_state['current_section_output'][section_key]['output'])

                        col_save, col_proceed = st.columns(2)
                        with col_save:
                            if st.button("💾 Save", type="primary", key=f"{section_type}_save"):
                                title = st.session_state.get('title_of_invention', '')
                                save_section_and_notify_memori(section_type, title, st.session_state['current_section_output'][section_key]['query'], st.session_state['current_section_output'][section_key]['output'])
                                st.success("✅ Saved!")

                        with col_proceed:
                            if st.session_state['patent_sections_db'].get_section('technical_advantages'):
                                if st.button("➡️ Proceed", key=f"{section_type}_proceed"):
                                    unlock_next_tab('technical_advantages')
                                    st.session_state['current_section_output'].pop(section_key, None)
                                    st.rerun()

                    saved_section = st.session_state['patent_sections_db'].get_section('technical_advantages')
                    if saved_section:
                        st.markdown("---")
                        st.markdown("### Saved Technical Advantages")
                        with st.expander(f"View Saved (ID: {saved_section['id']})"):
                            for para_num, para_text in saved_section['paragraphs']:
                                st.markdown(f"**{para_num}** {para_text}\n")

            # ================================================================
            # TAB 5: SUMMARY PARAPHRASE (Claim-to-Specification Conversion)
            # ================================================================
            with tabs[5]:
                if not st.session_state['tabs_unlocked']['summary_paraphrase']:
                    st.warning("⚠️ Complete Technical Advantages section first")
                else:
                    section_type = 'summary_paraphrase'
                    section_key = f'{section_type}_output'
                    st.markdown("### Summary Paraphrase (Claim Conversion)")
                    st.info("This section converts patent claims to specification paragraphs using standardized templates")

                    # Load and display all claims from patent-claims namespace
                    st.markdown("#### Claims Loaded from Database")
                    all_claims = st.session_state['patent_db'].get_all_claims()

                    if all_claims:
                        st.success(f"✅ {len(all_claims)} claims loaded from 'patent-claims' database")

                        # Display claims in expander
                        with st.expander("View All Claims"):
                            for claim_num, claim_text in all_claims:
                                st.markdown(f"**Claim {claim_num}:**")
                                st.text_area(f"Claim {claim_num}", value=claim_text, height=150, disabled=True, key=f"view_claim_{claim_num}")
                    else:
                        st.error("❌ No claims found in database. Please upload Patent Claims document first.")

                    st.markdown("---")

                    # Display admin-configured prompt (non-editable)
                    system_prompt = display_system_prompt('summary_paraphrase', "Summary Paraphrase Prompt")
                    query = st.text_area("Query Input", placeholder="Convert all claims to specification paragraphs...", height=100, key=f"{section_type}_query")

                    if st.button("Generate Claim Conversion", type="primary", key=f"{section_type}_generate"):
                        if not query:
                            st.error("⚠️ Please enter a query")
                        elif not all_claims:
                            st.error("⚠️ No claims found. Please upload Patent Claims document first.")
                        else:
                            with st.spinner("Converting claims to specification paragraphs..."):
                                try:
                                    # Get title from database
                                    title = st.session_state.get('title_of_invention', 'Title not found')

                                    # Format all claims for Claude API
                                    claims_text = ""
                                    for claim_num, claim_text_val in all_claims:
                                        claims_text += f"\n\nClaim {claim_num}:\n{claim_text_val}"

                                    # Build user message with all claims
                                    user_message = f"""Title of Invention: {title}

ALL PATENT CLAIMS:
{claims_text}

User Query: {query}

Please convert ALL claims above to specification paragraphs using the exact template provided in the system prompt. Include:
1. Independent method claim conversion (starting with [0024])
2. Dependent method claims (each as "In some embodiments,...")
3. Independent system claim conversion (if present)
4. Independent computer program product claim conversion (if present)

Maintain exact technical terminology and preserve claim language."""

                                    # Call Claude API directly (Memori intercepts)
                                    response = st.session_state['anthropic_client'].messages.create(
                                        model="claude-sonnet-4-20250514",
                                        max_tokens=4096,
                                        system=system_prompt,
                                        messages=[{
                                            "role": "user",
                                            "content": user_message
                                        }]
                                    )

                                    output = response.content[0].text.strip()

                                    # Store output
                                    st.session_state['current_section_output'][section_key] = {
                                        "query": query,
                                        "output": output,
                                        "claims_count": len(all_claims)
                                    }

                                    st.success(f"✅ Converted {len(all_claims)} claims to specification paragraphs!")
                                    st.rerun()

                                except Exception as e:
                                    st.error(f"Error converting claims: {str(e)}")

                    if section_key in st.session_state['current_section_output']:
                        st.markdown("---")
                        st.markdown(st.session_state['current_section_output'][section_key]['output'])

                        col_save, col_proceed = st.columns(2)
                        with col_save:
                            if st.button("💾 Save", type="primary", key=f"{section_type}_save"):
                                title = st.session_state.get('title_of_invention', '')
                                save_section_and_notify_memori(section_type, title, st.session_state['current_section_output'][section_key]['query'], st.session_state['current_section_output'][section_key]['output'])
                                st.success("✅ Saved!")

                        with col_proceed:
                            if st.session_state['patent_sections_db'].get_section('summary_paraphrase'):
                                if st.button("➡️ Proceed", key=f"{section_type}_proceed"):
                                    unlock_next_tab('summary_paraphrase')
                                    st.session_state['current_section_output'].pop(section_key, None)
                                    st.rerun()

                    saved_section = st.session_state['patent_sections_db'].get_section('summary_paraphrase')
                    if saved_section:
                        st.markdown("---")
                        st.markdown("### Saved Summary Paraphrase")
                        with st.expander(f"View Saved (ID: {saved_section['id']})"):
                            for para_num, para_text in saved_section['paragraphs']:
                                st.markdown(f"**{para_num}** {para_text}\n")

            # ================================================================
            # TAB 6: FIGURE 2 INTRODUCTION (Multi-Source Context + Vision API)
            # ================================================================
            with tabs[6]:
                if not st.session_state['tabs_unlocked']['figure2_intro']:
                    st.warning("⚠️ Complete Summary Paraphrase section first")
                else:
                    section_type = 'figure2_intro'
                    section_key = f'{section_type}_output'
                    st.markdown("### Figure 2 Introduction")
                    st.info("Upload Figure 2 screenshot to extract components, positioning, and labels using Claude Vision API")

                    # FRONTEND VALIDATION - Show context loading status
                    st.markdown("#### Context Validation")

                    validation_col1, validation_col2, validation_col3 = st.columns(3)

                    # INPUT(I): Validate Patent Claims from SQLite
                    with validation_col1:
                        claims = st.session_state['patent_db'].get_all_claims()
                        if claims:
                            st.success(f"✅ INPUT(I): {len(claims)} Claims loaded from SQLite")
                        else:
                            st.error("❌ INPUT(I): Claims not found")

                    # INPUT(II): Validate Screenshot Upload Status
                    with validation_col2:
                        fig2_uploaded = st.session_state.get('fig2_image_uploaded', False)
                        if fig2_uploaded:
                            st.success("✅ INPUT(II): Figure 2 screenshot processed")
                        else:
                            st.warning("⚠️ INPUT(II): Upload Figure 2 screenshot")

                    # INPUT(III): Validate Context from general-docs
                    with validation_col3:
                        if st.session_state['index'] is not None:
                            st.success("✅ INPUT(III): Context from 'general-docs' loaded")
                        else:
                            st.error("❌ INPUT(III): Vector database not loaded")

                    st.markdown("---")

                    # Display admin-configured prompts (non-editable)
                    vision_system_prompt = display_system_prompt('figure2_vision', "Figure 2 Vision Analysis Prompt")
                    intro_system_prompt = display_system_prompt('figure2_intro', "Figure 2 Introduction Prompt")

                    # STEP 1: Image Upload & Vision Processing
                    st.markdown("#### Step 1: Upload Figure 2 Screenshot")

                    # File uploader for Figure 2 image
                    fig2_image = st.file_uploader(
                        "Upload Figure 2 (JPG/PNG)",
                        type=['jpg', 'jpeg', 'png'],
                        key="fig2_image_uploader",
                        help="Upload a screenshot of Figure 2 to extract components and positioning"
                    )

                    # Show uploaded image
                    if fig2_image:
                        st.image(fig2_image, caption="Figure 2 Screenshot", use_column_width=True)

                    # Process Image Button
                    if fig2_image and st.button("Process Image with Claude Vision", type="primary", key="fig2_process_image"):
                        with st.spinner("Processing image with Claude Vision API..."):
                            try:
                                import base64

                                # Convert uploaded image to base64
                                image_bytes = fig2_image.getvalue()
                                image_base64 = base64.b64encode(image_bytes).decode('utf-8')

                                # Determine image type
                                image_type = fig2_image.type  # e.g., 'image/jpeg' or 'image/png'

                                # Get admin-configured vision prompt
                                vision_prompt = get_system_prompt('figure2_vision')

                                # Call Claude Vision API
                                response = st.session_state['anthropic_client'].messages.create(
                                    model="claude-sonnet-4-20250514",
                                    max_tokens=2048,
                                    messages=[{
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "image",
                                                "source": {
                                                    "type": "base64",
                                                    "media_type": image_type,
                                                    "data": image_base64
                                                }
                                            },
                                            {
                                                "type": "text",
                                                "text": vision_prompt
                                            }
                                        ]
                                    }]
                                )

                                # Extract structured data from response
                                vision_output = response.content[0].text

                                # Store extracted information
                                st.session_state['fig2_vision_data'] = vision_output
                                st.session_state['fig2_image_bytes'] = image_bytes

                                st.success("✅ Image processed successfully!")
                                st.markdown("### Extracted Information")
                                st.text_area("Vision API Output", value=vision_output, height=300, disabled=True, key="fig2_vision_output_display")

                                st.rerun()

                            except Exception as e:
                                st.error(f"Error processing image: {str(e)}")
                                import traceback
                                st.error(traceback.format_exc())

                    # STEP 2: Convert to Embeddings & Store in Pinecone
                    if st.session_state.get('fig2_vision_data') and not st.session_state.get('fig2_image_uploaded', False):
                        st.markdown("---")
                        st.markdown("#### Step 2: Save to Vector Database")
                        st.info("Convert extracted image data to embeddings and store in Pinecone namespace 'fig-2'")

                        if st.button("Convert to Embeddings & Save to Vector DB", type="primary", key="fig2_save_embeddings"):
                            with st.spinner("Converting image data to embeddings and saving to 'fig-2' namespace..."):
                                try:
                                    from llama_index.core import Document

                                    # Create a document from vision output
                                    vision_text = st.session_state['fig2_vision_data']

                                    # Create LlamaIndex Document
                                    fig2_doc = Document(
                                        text=f"""Figure 2 Analysis:

{vision_text}

This is the extracted information from the Figure 2 diagram uploaded by the user.
Components, positioning, text labels, and relationships have been identified using Claude Vision API.
""",
                                        metadata={
                                            "source": "figure2_screenshot",
                                            "type": "vision_extraction",
                                            "section": "figure2_intro"
                                        }
                                    )

                                    # Create index in 'fig-2' namespace
                                    from llama_index.core import VectorStoreIndex, StorageContext
                                    from llama_index.vector_stores.pinecone import PineconeVectorStore

                                    # Create Pinecone vector store with 'fig-2' namespace
                                    vector_store = PineconeVectorStore(
                                        pinecone_index=st.session_state['pinecone_index'],
                                        namespace="fig-2"
                                    )

                                    storage_context = StorageContext.from_defaults(vector_store=vector_store)

                                    # Create index from document
                                    fig2_index = VectorStoreIndex.from_documents(
                                        [fig2_doc],
                                        storage_context=storage_context
                                    )

                                    # Store in session state
                                    st.session_state['fig2_index'] = fig2_index
                                    st.session_state['fig2_image_uploaded'] = True

                                    # Frontend confirmation
                                    st.success("✅ Image data converted to embeddings and saved to Pinecone namespace 'fig-2'!")
                                    st.balloons()
                                    st.rerun()

                                except Exception as e:
                                    st.error(f"Error saving to vector database: {str(e)}")
                                    import traceback
                                    st.error(traceback.format_exc())

                    # STEP 3: Generate Figure 2 Introduction with Multi-Source Context
                    if st.session_state.get('fig2_image_uploaded', False):
                        st.markdown("---")
                        st.markdown("#### Step 3: Generate Figure 2 Introduction")

                        # System Prompt
                        default_prompt = """You are an expert patent writer. Generate a comprehensive introduction to Figure 2.

CONTEXT SOURCES AVAILABLE:
1. **Figure 2 Visual Data** (from 'fig-2' namespace): Extracted components, positioning, text labels
2. **Patent Claims** (from 'patent-claims' namespace + SQLite): All independent and dependent claims
3. **General Documents** (from 'general-docs' namespace): PPTX, DOCX, invention details
4. **Previous Sections** (via Memori): Background, Summary, Drawings, Technical Problems/Advantages

INSTRUCTIONS:
- Introduce Figure 2 as a diagram illustrating the environment for this invention
- Reference specific components extracted from the uploaded screenshot
- Connect Figure 2 to the patent claims (mention which claims it enables)
- Explain the purpose and significance of Figure 2 in the overall invention
- Use proper positioning language based on the extracted spatial layout

OUTPUT FORMAT:
Multiple paragraphs describing Figure 2 introduction, using proper paragraph numbering based on previous sections."""

                        system_prompt = st.text_area("System Prompt", value=default_prompt, height=250, key="fig2_intro_system_prompt")
                        query = st.text_area("Query Input", placeholder="Generate Figure 2 introduction based on uploaded screenshot and patent claims...", height=100, key="fig2_intro_query")

                        # Generate Button
                        if st.button("Generate Figure 2 Introduction", type="primary", key="fig2_intro_generate"):
                            if not query:
                                st.error("⚠️ Please enter a query")
                            else:
                                with st.spinner("Generating Figure 2 Introduction with multi-source context..."):
                                    try:
                                        # MULTI-SOURCE CONTEXT RETRIEVAL

                                        # 1. Retrieve from 'fig-2' namespace (uploaded image data)
                                        fig2_retriever = st.session_state['fig2_index'].as_retriever(similarity_top_k=3)
                                        fig2_nodes = fig2_retriever.retrieve(query)
                                        fig2_context = "\n".join([node.text for node in fig2_nodes])

                                        # 2. Retrieve from 'general-docs' namespace
                                        general_retriever = st.session_state['index'].as_retriever(similarity_top_k=3)
                                        general_nodes = general_retriever.retrieve(query)
                                        general_context = "\n".join([node.text for node in general_nodes])

                                        # 3. Get patent claims from SQLite
                                        claims = st.session_state['patent_db'].get_all_claims()
                                        claims_text = ""
                                        for claim_num, claim_text_val in claims[:5]:  # First 5 claims
                                            claims_text += f"\nClaim {claim_num}: {claim_text_val[:300]}...\n"

                                        # 4. Get previously saved sections (via patent_sections_db)
                                        previous_sections = st.session_state['patent_sections_db'].get_all_sections_context()

                                        # 5. Get title
                                        title = st.session_state.get('title_of_invention', 'Title not found')

                                        # Build enhanced context
                                        enhanced_context = f"""
=== CONTEXT FOR FIGURE 2 INTRODUCTION ===

TITLE OF INVENTION:
{title}

FIGURE 2 VISUAL ANALYSIS (from uploaded screenshot):
{fig2_context}

PATENT CLAIMS (Top 5):
{claims_text}

GENERAL DOCUMENT CONTEXT:
{general_context}

PREVIOUSLY COMPLETED SECTIONS:
{previous_sections}

===================================
"""

                                        # Enhanced system prompt
                                        full_system_prompt = system_prompt + f"\n\n{enhanced_context}"

                                        # Call Claude API (Memori intercepts - provides additional session awareness)
                                        response = st.session_state['anthropic_client'].messages.create(
                                            model="claude-sonnet-4-20250514",
                                            max_tokens=4096,
                                            system=full_system_prompt,
                                            messages=[{
                                                "role": "user",
                                                "content": f"""USER QUERY:
{query}

Please generate a comprehensive Figure 2 Introduction using ALL available context sources:
1. Figure 2 visual analysis (components, positioning, labels)
2. Patent claims that Figure 2 enables
3. General document context
4. Previously written sections

Make sure to:
- Reference specific components from the uploaded Figure 2 screenshot
- Explain how Figure 2 relates to the patent claims
- Use proper patent language and formatting"""
                                            }]
                                        )

                                        output = response.content[0].text.strip()

                                        # Store output
                                        st.session_state['current_section_output'][section_key] = {
                                            "query": query,
                                            "output": output,
                                            "sources": {
                                                "fig2": True,
                                                "claims": len(claims),
                                                "general_docs": len(general_nodes),
                                                "previous_sections": bool(previous_sections)
                                            }
                                        }

                                        st.success("✅ Figure 2 Introduction generated with multi-source context!")
                                        st.rerun()

                                    except Exception as e:
                                        st.error(f"Error generating: {str(e)}")
                                        import traceback
                                        st.error(traceback.format_exc())

                    # Display Generated Content
                    if section_key in st.session_state['current_section_output']:
                        st.markdown("---")
                        st.markdown("### Generated Figure 2 Introduction")

                        output_data = st.session_state['current_section_output'][section_key]

                        # Show sources used
                        st.info(f"""**Context Sources Used:**
- ✅ Figure 2 Screenshot Data (from 'fig-2' namespace)
- ✅ {output_data['sources']['claims']} Patent Claims (from SQLite + 'patent-claims' namespace)
- ✅ {output_data['sources']['general_docs']} General Documents (from 'general-docs' namespace)
- {'✅' if output_data['sources']['previous_sections'] else '❌'} Previous Sections (via Memori)
""")

                        # Display generated text
                        st.markdown(output_data['output'])

                        # Save and Proceed Buttons
                        col_save, col_proceed = st.columns(2)

                        with col_save:
                            if st.button("💾 Save Figure 2 Introduction", type="primary", key="fig2_intro_save"):
                                title = st.session_state.get('title_of_invention', 'Figure 2 Introduction')
                                query_text = output_data['query']
                                content = output_data['output']

                                try:
                                    section_id = save_section_and_notify_memori('figure2_intro', title, query_text, content)
                                    st.success(f"✅ Figure 2 Introduction saved! (ID: {section_id})")
                                    st.balloons()
                                except Exception as e:
                                    st.error(f"❌ Error saving: {str(e)}")

                        with col_proceed:
                            if st.session_state['patent_sections_db'].get_section('figure2_intro'):
                                if st.button("➡️ Proceed to Sequencing", key="fig2_intro_proceed"):
                                    unlock_next_tab('figure2_intro')
                                    st.session_state['current_section_output'].pop(section_key, None)
                                    st.success("✅ Sequencing tab unlocked!")
                                    st.rerun()
                            else:
                                st.info("💾 Save first to proceed")

                    # Show Saved Section
                    saved_section = st.session_state['patent_sections_db'].get_section('figure2_intro')
                    if saved_section:
                        st.markdown("---")
                        st.markdown("### Saved Figure 2 Introduction")
                        with st.expander(f"View Saved (ID: {saved_section['id']})"):
                            for para_num, para_text in saved_section['paragraphs']:
                                st.markdown(f"**{para_num}** {para_text}\n")

            # ================================================================
            # TAB 7: SEQUENCING (Claim Feature Extraction & Ordering)
            # ================================================================
            with tabs[7]:
                if not st.session_state['tabs_unlocked']['sequencing']:
                    st.warning("⚠️ Complete Figure 2 Introduction section first")
                else:
                    st.markdown("### Sequencing: Claim Feature Extraction & Ordering")
                    st.info("Extract claim features and arrange them in operational sequence")

                    # Display admin-configured prompt (non-editable)
                    sequencing_system_prompt = display_system_prompt('sequencing', "Sequencing Prompt")

                    # STEP 1: Fetch and Display All Claims
                    st.markdown("#### Step 1: Patent Claims from Database")

                    all_claims = st.session_state['patent_db'].get_all_claims()

                    if all_claims:
                        st.success(f"✅ {len(all_claims)} claims loaded from patent database")

                        # Display all claims in expander
                        with st.expander("View All Claims", expanded=False):
                            for claim_num, claim_text in all_claims:
                                st.markdown(f"**Claim {claim_num}:**")
                                st.text_area(
                                    f"Claim {claim_num}",
                                    value=claim_text,
                                    height=150,
                                    disabled=True,
                                    key=f"sequencing_claim_{claim_num}_display",
                                    label_visibility="collapsed"
                                )
                                st.markdown("---")
                    else:
                        st.error("❌ No claims found in database. Please upload Patent Claims document first.")

                    st.markdown("---")

                    # STEP 2: Automatic Sequencing Button
                    st.markdown("#### Step 2: Extract Features & Generate Sequence")
                    st.info("""This will automatically:
1. Break down claims into individual claim features (C#F#)
2. Convert each feature to system description format
3. Arrange features in operational sequence (step-by-step flow)
""")

                    if st.button("🔄 Sequence Claims", type="primary", key="sequencing_button"):
                        if not all_claims:
                            st.error("⚠️ No claims available to sequence")
                        else:
                            with st.spinner("Extracting claim features and generating operational sequence..."):
                                try:
                                    # Format all claims for Claude API
                                    claims_text = ""
                                    for claim_num, claim_text_val in all_claims:
                                        claims_text += f"\n\nClaim {claim_num}:\n{claim_text_val}"

                                    # Get admin-configured sequencing prompt
                                    conversion_rules = get_system_prompt('sequencing')

                                    # Call Claude API for sequencing
                                    response = st.session_state['anthropic_client'].messages.create(
                                        model="claude-sonnet-4-20250514",
                                        max_tokens=8000,
                                        system=conversion_rules,
                                        messages=[{
                                            "role": "user",
                                            "content": f"""Here are all the patent claims to analyze:

{claims_text}

Please:
1. Extract and convert all claim features following the conversion rules
2. Arrange them in operational sequence (step-by-step flow of the invention)

Provide both the extracted features and the final sequenced order."""
                                        }]
                                    )

                                    sequencing_output = response.content[0].text.strip()

                                    # Store in session state
                                    st.session_state['claim_features_extracted'] = sequencing_output
                                    st.session_state['sequencing_output'] = sequencing_output

                                    st.success("✅ Claim features extracted and sequenced successfully!")
                                    st.rerun()

                                except Exception as e:
                                    st.error(f"Error during sequencing: {str(e)}")
                                    import traceback
                                    st.error(traceback.format_exc())

                    # STEP 3: Display Sequencing Output
                    if st.session_state.get('sequencing_output'):
                        st.markdown("---")
                        st.markdown("### Sequencing Results")

                        # Add custom CSS for claim feature boxes
                        st.markdown("""
                        <style>
                        .claim-feature-box {
                            border: 3px solid #1e3a8a;
                            padding: 20px;
                            margin: 15px 0;
                            background-color: white;
                            display: flex;
                            align-items: center;
                            border-radius: 5px;
                        }
                        .claim-feature-circle {
                            width: 80px;
                            height: 80px;
                            border: 3px solid #1e3a8a;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-weight: bold;
                            font-size: 18px;
                            margin-right: 20px;
                            flex-shrink: 0;
                            background-color: white;
                        }
                        .claim-feature-text {
                            flex: 1;
                            font-size: 16px;
                            line-height: 1.6;
                        }
                        </style>
                        """, unsafe_allow_html=True)

                        # Parse sequencing output to extract individual features
                        sequencing_text = st.session_state['sequencing_output']

                        # Extract the "SEQUENCED OPERATIONAL FLOW" section
                        if "=== SEQUENCED OPERATIONAL FLOW ===" in sequencing_text:
                            # Split and get the sequenced section
                            parts = sequencing_text.split("=== SEQUENCED OPERATIONAL FLOW ===")
                            if len(parts) > 1:
                                sequenced_section = parts[1].strip()

                                # Parse each line starting with C#F#
                                import re
                                lines = sequenced_section.split('\n')
                                claim_features = []

                                for line in lines:
                                    line = line.strip()
                                    # Match pattern: C#F# = [text]
                                    match = re.match(r'^(C\d+F\d+)\s*=\s*\[(.*)\]$', line)
                                    if match:
                                        feature_id = match.group(1)
                                        feature_text = match.group(2)
                                        claim_features.append((feature_id, feature_text))

                                # Initialize or update the sequenced_features_list
                                if not st.session_state['sequenced_features_list'] or not st.session_state['custom_order_modified']:
                                    st.session_state['sequenced_features_list'] = claim_features.copy()

                                # Display claim features in formatted boxes with reordering controls
                                st.markdown("#### Sequenced Claim Features (Operational Flow)")
                                st.info("💡 Use ⬆️ and ⬇️ buttons to reorder claim features if you want to adjust the sequence")

                                # Display each claim feature with up/down buttons
                                for idx, (feature_id, feature_text) in enumerate(st.session_state['sequenced_features_list']):
                                    # Create columns: buttons on left, feature box on right
                                    col_buttons, col_feature = st.columns([0.15, 0.85])

                                    with col_buttons:
                                        # Up button (disabled if first item)
                                        if idx > 0:
                                            if st.button("⬆️", key=f"up_{feature_id}_{idx}", help="Move up"):
                                                # Swap with previous item
                                                st.session_state['sequenced_features_list'][idx], st.session_state['sequenced_features_list'][idx-1] = \
                                                    st.session_state['sequenced_features_list'][idx-1], st.session_state['sequenced_features_list'][idx]
                                                st.session_state['custom_order_modified'] = True
                                                st.rerun()
                                        else:
                                            st.button("⬆️", key=f"up_{feature_id}_{idx}_disabled", disabled=True)

                                        # Down button (disabled if last item)
                                        if idx < len(st.session_state['sequenced_features_list']) - 1:
                                            if st.button("⬇️", key=f"down_{feature_id}_{idx}", help="Move down"):
                                                # Swap with next item
                                                st.session_state['sequenced_features_list'][idx], st.session_state['sequenced_features_list'][idx+1] = \
                                                    st.session_state['sequenced_features_list'][idx+1], st.session_state['sequenced_features_list'][idx]
                                                st.session_state['custom_order_modified'] = True
                                                st.rerun()
                                        else:
                                            st.button("⬇️", key=f"down_{feature_id}_{idx}_disabled", disabled=True)

                                    with col_feature:
                                        # Create HTML for each claim feature box
                                        html_box = f"""
                                        <div class="claim-feature-box">
                                            <div class="claim-feature-circle">{feature_id}</div>
                                            <div class="claim-feature-text">{feature_text}</div>
                                        </div>
                                        """
                                        st.markdown(html_box, unsafe_allow_html=True)

                                # Show indicator if user has modified the order
                                if st.session_state['custom_order_modified']:
                                    st.success("✅ Custom order applied! You have modified the sequence.")

                                    # Reset to original order button
                                    if st.button("🔄 Reset to Original AI Sequence", key="reset_sequence"):
                                        st.session_state['sequenced_features_list'] = claim_features.copy()
                                        st.session_state['custom_order_modified'] = False
                                        st.rerun()

                        # Also show raw output in expander for reference
                        with st.expander("View Full Sequencing Output (Raw)", expanded=False):
                            st.text_area(
                                "Complete Extraction & Sequencing",
                                value=st.session_state['sequencing_output'],
                                height=400,
                                disabled=True,
                                key="sequencing_output_raw_display"
                            )

                        # Save and Proceed Buttons
                        col_save, col_proceed = st.columns(2)

                        with col_save:
                            if st.button("💾 Save Sequencing", type="primary", key="sequencing_save"):
                                title = st.session_state.get('title_of_invention', 'Claim Sequencing')

                                # Build content from current sequenced_features_list (respects user's custom order)
                                final_sequence_lines = []
                                final_sequence_lines.append("=== FINAL SEQUENCED OPERATIONAL FLOW ===\n")

                                for feature_id, feature_text in st.session_state['sequenced_features_list']:
                                    final_sequence_lines.append(f"{feature_id} = [{feature_text}]")

                                final_content = "\n".join(final_sequence_lines)

                                # Add indicator if custom order was used
                                if st.session_state['custom_order_modified']:
                                    final_content = "=== USER-MODIFIED SEQUENCE ===\n\n" + final_content
                                else:
                                    final_content = "=== AI-GENERATED SEQUENCE ===\n\n" + final_content

                                try:
                                    # Save to patent_sections_db
                                    section_id = save_section_and_notify_memori(
                                        'sequencing',
                                        title,
                                        f"Sequenced {len(all_claims)} claims" + (" (custom order)" if st.session_state['custom_order_modified'] else ""),
                                        final_content
                                    )
                                    st.success(f"✅ Sequencing saved! (ID: {section_id})")
                                    st.balloons()
                                except Exception as e:
                                    st.error(f"❌ Error saving: {str(e)}")

                        with col_proceed:
                            if st.session_state['patent_sections_db'].get_section('sequencing'):
                                if st.button("➡️ Proceed to Figure 2 Enablement", key="sequencing_proceed"):
                                    unlock_next_tab('sequencing')
                                    st.success("✅ Figure 2 Enablement tab unlocked!")
                                    st.rerun()
                            else:
                                st.info("💾 Save first to proceed")

                    # Show Saved Sequencing
                    saved_section = st.session_state['patent_sections_db'].get_section('sequencing')
                    if saved_section:
                        st.markdown("---")
                        st.markdown("### Saved Sequencing")
                        with st.expander(f"View Saved Sequencing (ID: {saved_section['id']})"):
                            for para_num, para_text in saved_section['paragraphs']:
                                st.markdown(f"**{para_num}** {para_text}\n")

            # ================================================================
            # TAB 8: FIGURE 2 CLAIM ENABLEMENT (Sequential Claim Feature Processing)
            # ================================================================
            with tabs[8]:
                if not st.session_state['tabs_unlocked']['figure2_enablement']:
                    st.warning("⚠️ Complete Sequencing section first")
                else:
                    st.markdown("### Figure 2 Claim Feature Enablement")
                    st.info("Process each claim feature sequentially - enable one by one until all are completed")

                    # Display admin-configured prompt (non-editable)
                    enablement_system_prompt = display_system_prompt('figure2_enablement', "Claim Enablement Prompt")

                    # Load sequenced features from session state or SQLite
                    features_list = st.session_state.get('sequenced_features_list', [])

                    # If features_list is empty, try to load from saved sequencing
                    if not features_list:
                        saved_sequencing = st.session_state['patent_sections_db'].get_section('sequencing')
                        if saved_sequencing:
                            import re
                            for para_num, para_text in saved_sequencing['paragraphs']:
                                # Parse: C#F# = [text]
                                match = re.match(r'^(C\d+F\d+)\s*=\s*\[(.*)\]$', para_text.strip())
                                if match:
                                    feature_id = match.group(1)
                                    feature_text = match.group(2)
                                    features_list.append((feature_id, feature_text))
                            st.session_state['sequenced_features_list'] = features_list

                    total_features = len(features_list)
                    current_index = st.session_state['current_feature_index']

                    # Check if all features are enabled
                    if current_index >= total_features and total_features > 0:
                        st.session_state['all_features_enabled'] = True

                    # CONTEXT VALIDATION UI
                    st.markdown("#### Context Validation")
                    val_col1, val_col2, val_col3, val_col4 = st.columns(4)

                    with val_col1:
                        if st.session_state.get('memori_initialized', False):
                            st.success("✅ 1. MEMORI CONTEXT LOADED")
                        else:
                            st.error("❌ 1. MEMORI NOT LOADED")

                    with val_col2:
                        claims = st.session_state['patent_db'].get_all_claims() if st.session_state['patent_db'] else []
                        if claims:
                            st.success("✅ 2. PATENT-CLAIMS LOADED")
                        else:
                            st.error("❌ 2. PATENT-CLAIMS NOT LOADED")

                    with val_col3:
                        if st.session_state.get('fig2_index'):
                            st.success("✅ 3. FIG-2 VECTOR DB LOADED")
                        else:
                            st.warning("⚠️ 3. FIG-2 VECTOR DB")

                    with val_col4:
                        if st.session_state['index']:
                            st.success("✅ 4. GENERAL-DOCS LOADED")
                        else:
                            st.error("❌ 4. GENERAL-DOCS NOT LOADED")

                    st.markdown("**1+2+3+4** all are used to write the answers in the OUTPUT BOX")
                    st.markdown("**(1+2+3+4) as CONTEXT + SYSTEM PROMPT + QUERY INPUT → LLM**")

                    st.markdown("---")

                    # Check if all features enabled - show completion message
                    if st.session_state['all_features_enabled']:
                        st.success(f"🎉 All {total_features} claim features have been enabled!")
                        st.markdown("### All Claim Features Completed")

                        # Show all enabled features
                        with st.expander("View All Enabled Features", expanded=False):
                            for feat_id, feat_output in st.session_state['enabled_features'].items():
                                st.markdown(f"**{feat_id}:**")
                                st.text_area(f"Output for {feat_id}", value=feat_output, height=100, disabled=True, key=f"view_enabled_{feat_id}")

                        # Proceed to Scenario Diagrams
                        if st.button("➡️ Proceed to Scenario Diagrams", type="primary", key="enablement_to_scenarios"):
                            unlock_next_tab('figure2_enablement')
                            st.success("✅ Scenario Diagrams tab unlocked!")
                            st.rerun()

                    elif total_features > 0:
                        # Show progress
                        st.markdown(f"#### Feature {current_index + 1} of {total_features}")
                        progress = current_index / total_features
                        st.progress(progress, text=f"Progress: {current_index}/{total_features} features enabled")

                        # Get current feature
                        current_feature_id, current_feature_text = features_list[current_index]

                        # Add CSS for claim feature box
                        st.markdown("""
                        <style>
                        .enablement-feature-box {
                            border: 3px solid #1e3a8a;
                            padding: 20px;
                            margin: 15px 0;
                            background-color: #f8fafc;
                            display: flex;
                            align-items: flex-start;
                            border-radius: 8px;
                        }
                        .enablement-feature-circle {
                            width: 70px;
                            height: 70px;
                            border: 3px solid #1e3a8a;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-weight: bold;
                            font-size: 16px;
                            margin-right: 20px;
                            flex-shrink: 0;
                            background-color: white;
                        }
                        .enablement-feature-text {
                            flex: 1;
                            font-size: 15px;
                            line-height: 1.6;
                        }
                        </style>
                        """, unsafe_allow_html=True)

                        # Display current claim feature
                        st.markdown("##### Current Claim Feature (Auto-loaded from SQLite)")
                        html_box = f"""
                        <div class="enablement-feature-box">
                            <div class="enablement-feature-circle">{current_feature_id}</div>
                            <div class="enablement-feature-text">{current_feature_text}</div>
                        </div>
                        """
                        st.markdown(html_box, unsafe_allow_html=True)

                        st.markdown("---")

                        # Two-column layout: Left (Output Box), Right (System Prompt & Query Input)
                        col_left, col_right = st.columns([0.6, 0.4])

                        with col_right:
                            st.markdown("##### SYSTEM PROMPT:")
                            default_system_prompt = f"""You are an expert patent writer. Generate detailed enablement text for the claim feature shown.

The claim feature is: {current_feature_id}
Feature text: {current_feature_text}

Using the context from:
1. Memori (session memory)
2. Patent claims database
3. Figure 2 vector database (fig-2 namespace)
4. General documents (general-docs namespace)

Write a comprehensive technical description explaining how this claim feature is enabled by the system/invention. Include specific references to components, data flows, and technical operations."""

                            system_prompt = st.text_area(
                                "System Prompt",
                                value=default_system_prompt,
                                height=200,
                                key=f"enablement_system_prompt_{current_index}",
                                label_visibility="collapsed"
                            )

                            st.markdown("##### QUERY INPUT:")
                            query_input = st.text_area(
                                "Query Input",
                                placeholder=f"Enter additional instructions for generating enablement for {current_feature_id}...",
                                height=150,
                                key=f"enablement_query_{current_index}",
                                help="Change in query input changes the answer in the output box",
                                label_visibility="collapsed"
                            )

                            # Generate button
                            if st.button("🔄 Generate Enablement", type="primary", key=f"generate_enablement_{current_index}"):
                                if not query_input:
                                    st.error("⚠️ Please enter a query")
                                else:
                                    with st.spinner(f"Generating enablement for {current_feature_id}..."):
                                        try:
                                            # Multi-source context retrieval
                                            context_parts = []

                                            # 1. Get from fig-2 namespace
                                            if st.session_state.get('fig2_index'):
                                                fig2_retriever = st.session_state['fig2_index'].as_retriever(similarity_top_k=3)
                                                fig2_nodes = fig2_retriever.retrieve(query_input)
                                                fig2_context = "\n".join([node.text for node in fig2_nodes])
                                                context_parts.append(f"=== FIG-2 CONTEXT ===\n{fig2_context}")

                                            # 2. Get from general-docs namespace
                                            if st.session_state['index']:
                                                general_retriever = st.session_state['index'].as_retriever(similarity_top_k=3)
                                                general_nodes = general_retriever.retrieve(query_input)
                                                general_context = "\n".join([node.text for node in general_nodes])
                                                context_parts.append(f"=== GENERAL-DOCS CONTEXT ===\n{general_context}")

                                            # 3. Get patent claims
                                            if st.session_state['patent_db']:
                                                claims = st.session_state['patent_db'].get_all_claims()
                                                claims_text = "\n".join([f"Claim {num}: {text[:200]}..." for num, text in claims[:5]])
                                                context_parts.append(f"=== PATENT CLAIMS ===\n{claims_text}")

                                            # 4. Get previous enabled features
                                            if st.session_state['enabled_features']:
                                                prev_features = "\n".join([f"{fid}: {ftext[:150]}..." for fid, ftext in st.session_state['enabled_features'].items()])
                                                context_parts.append(f"=== PREVIOUSLY ENABLED FEATURES ===\n{prev_features}")

                                            full_context = "\n\n".join(context_parts)

                                            # Call Claude API
                                            response = st.session_state['anthropic_client'].messages.create(
                                                model="claude-sonnet-4-20250514",
                                                max_tokens=4096,
                                                system=system_prompt + f"\n\nCONTEXT:\n{full_context}",
                                                messages=[{
                                                    "role": "user",
                                                    "content": f"""Generate enablement text for claim feature {current_feature_id}:

Feature: {current_feature_text}

User Query: {query_input}

Provide detailed technical description explaining how this claim feature is enabled."""
                                                }]
                                            )

                                            output = response.content[0].text.strip()
                                            st.session_state['current_feature_output'] = output
                                            st.rerun()

                                        except Exception as e:
                                            st.error(f"Error generating: {str(e)}")

                        with col_left:
                            st.markdown("##### OUTPUT BOX")
                            st.caption("The answer in the output box is editable. Using the cursor, the user can add or edit the responses by typing.")

                            # Editable output text area
                            edited_output = st.text_area(
                                "Editable Output",
                                value=st.session_state.get('current_feature_output', ''),
                                height=400,
                                key=f"output_box_{current_index}",
                                label_visibility="collapsed",
                                placeholder="Generated enablement text will appear here. You can edit it before saving."
                            )

                            # Update session state if user edits
                            if edited_output != st.session_state.get('current_feature_output', ''):
                                st.session_state['current_feature_output'] = edited_output

                            # Save button
                            if st.button("💾 Save", type="primary", key=f"save_enablement_{current_index}"):
                                if not edited_output.strip():
                                    st.error("⚠️ Output box is empty. Generate or type content first.")
                                else:
                                    with st.spinner("Saving to fig-2 vector database and SQLite..."):
                                        try:
                                            # 1. Save to fig-2 vector database
                                            from llama_index.core import Document, VectorStoreIndex, StorageContext
                                            from llama_index.vector_stores.pinecone import PineconeVectorStore

                                            enablement_doc = Document(
                                                text=f"""Claim Feature Enablement: {current_feature_id}

Feature: {current_feature_text}

Enablement Description:
{edited_output}
""",
                                                metadata={
                                                    "source": "claim_enablement",
                                                    "feature_id": current_feature_id,
                                                    "type": "enablement"
                                                }
                                            )

                                            # Add to fig-2 namespace
                                            vector_store = PineconeVectorStore(
                                                pinecone_index=st.session_state['pinecone_index'],
                                                namespace="fig-2"
                                            )
                                            storage_context = StorageContext.from_defaults(vector_store=vector_store)
                                            VectorStoreIndex.from_documents([enablement_doc], storage_context=storage_context)

                                            # 2. Save to SQLite
                                            save_section_and_notify_memori(
                                                f'enablement_{current_feature_id}',
                                                st.session_state.get('title_of_invention', ''),
                                                f"Enablement for {current_feature_id}",
                                                f"{current_feature_id}: {edited_output}"
                                            )

                                            # 3. Store in enabled_features
                                            st.session_state['enabled_features'][current_feature_id] = edited_output

                                            # 4. Move to next feature
                                            st.session_state['current_feature_index'] += 1
                                            st.session_state['current_feature_output'] = ""

                                            st.success(f"✅ {current_feature_id} saved to fig-2 vector DB and SQLite!")

                                            # Check if all done
                                            if st.session_state['current_feature_index'] >= total_features:
                                                st.session_state['all_features_enabled'] = True
                                                st.balloons()

                                            st.rerun()

                                        except Exception as e:
                                            st.error(f"❌ Error saving: {str(e)}")
                                            import traceback
                                            st.error(traceback.format_exc())

                        # Show previously enabled features
                        if st.session_state['enabled_features']:
                            st.markdown("---")
                            st.markdown("##### Previously Enabled Features")
                            with st.expander(f"View {len(st.session_state['enabled_features'])} enabled features", expanded=False):
                                for feat_id, feat_output in st.session_state['enabled_features'].items():
                                    st.markdown(f"**{feat_id}:** {feat_output[:200]}...")

                    else:
                        st.warning("⚠️ No sequenced features found. Please complete the Sequencing tab first.")

            # ================================================================
            # TAB 9: SCENARIO DIAGRAMS (Image Upload + Multi-Source Context)
            # ================================================================
            with tabs[9]:
                if not st.session_state['tabs_unlocked']['scenario_diagrams']:
                    st.warning("⚠️ Complete Figure 2 Claim Enablement section first")
                else:
                    st.markdown("### Scenario Diagrams")
                    st.info("Upload scenario diagram screenshots and generate descriptions using all context sources")

                    # Display admin-configured prompts (non-editable)
                    scenario_vision_prompt = display_system_prompt('scenario_vision', "Scenario Vision Analysis Prompt")
                    scenario_desc_prompt = display_system_prompt('scenario_diagram', "Scenario Diagram Description Prompt")

                    # Show scenario index (X_i = 1, 2, 3...)
                    current_scenario = st.session_state['current_scenario_index'] + 1
                    st.markdown(f"## X<sub>i</sub> = {current_scenario}", unsafe_allow_html=True)

                    # CONTEXT VALIDATION UI
                    st.markdown("#### Context Validation")
                    val_col1, val_col2, val_col3, val_col4 = st.columns(4)

                    with val_col1:
                        if st.session_state.get('memori_initialized', False):
                            st.success("✅ 1. MEMORI CONTEXT LOADED")
                        else:
                            st.warning("⚠️ 1. MEMORI CONTEXT")

                    with val_col2:
                        claims = st.session_state['patent_db'].get_all_claims() if st.session_state['patent_db'] else []
                        if claims:
                            st.success("✅ 2. PATENT-CLAIMS LOADED")
                        else:
                            st.error("❌ 2. PATENT-CLAIMS NOT LOADED")

                    with val_col3:
                        if st.session_state.get('fig2_index'):
                            st.success("✅ 3. FIG-2 VECTOR DB LOADED")
                        else:
                            st.warning("⚠️ 3. FIG-2 VECTOR DB")

                    with val_col4:
                        if st.session_state['index']:
                            st.success("✅ 4. GENERAL-DOCS LOADED")
                        else:
                            st.error("❌ 4. GENERAL-DOCS NOT LOADED")

                    st.markdown("**1+2+3+4** all are used to write the answers in the OUTPUT BOX")
                    st.markdown("**(1+2+3+4) as CONTEXT + SYSTEM PROMPT + QUERY INPUT → LLM**")

                    st.markdown("---")

                    # Main layout: Image Upload + Output on left, System Prompt + Query on right
                    col_left, col_right = st.columns([0.6, 0.4])

                    with col_left:
                        # Image Upload Section
                        st.markdown("##### Upload Screenshot of Scenario Diagram")
                        st.caption("Upload the screenshot of the scenario diagram or the PNG or JPEG image.")

                        scenario_image = st.file_uploader(
                            "Upload Scenario Diagram",
                            type=['jpg', 'jpeg', 'png'],
                            key=f"scenario_image_uploader_{current_scenario}",
                            help="Claude API will fetch and retrieve the context of the scenario diagram"
                        )

                        # Show uploaded image
                        if scenario_image:
                            st.image(scenario_image, caption=f"Scenario Diagram {current_scenario}", use_column_width=True)

                            # Process image with Claude Vision
                            if st.button("⬆️ Process Image with Claude Vision", type="secondary", key=f"process_scenario_{current_scenario}"):
                                with st.spinner("Processing scenario diagram with Claude Vision..."):
                                    try:
                                        import base64

                                        image_bytes = scenario_image.getvalue()
                                        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                                        image_type = scenario_image.type

                                        vision_response = st.session_state['anthropic_client'].messages.create(
                                            model="claude-sonnet-4-20250514",
                                            max_tokens=2048,
                                            messages=[{
                                                "role": "user",
                                                "content": [
                                                    {
                                                        "type": "image",
                                                        "source": {
                                                            "type": "base64",
                                                            "media_type": image_type,
                                                            "data": image_base64
                                                        }
                                                    },
                                                    {
                                                        "type": "text",
                                                        "text": """Analyze this scenario diagram and extract:
1. All components, actors, or entities shown
2. The flow or sequence of operations
3. Any text labels or annotations
4. The overall purpose/scenario being depicted

Provide a detailed description that can be used for patent documentation."""
                                                    }
                                                ]
                                            }]
                                        )

                                        vision_output = vision_response.content[0].text
                                        st.session_state[f'scenario_vision_{current_scenario}'] = vision_output

                                        # Save to fig-2 vector database
                                        from llama_index.core import Document, VectorStoreIndex, StorageContext
                                        from llama_index.vector_stores.pinecone import PineconeVectorStore

                                        scenario_doc = Document(
                                            text=f"Scenario Diagram {current_scenario} Analysis:\n{vision_output}",
                                            metadata={
                                                "source": f"scenario_diagram_{current_scenario}",
                                                "type": "vision_extraction"
                                            }
                                        )

                                        vector_store = PineconeVectorStore(
                                            pinecone_index=st.session_state['pinecone_index'],
                                            namespace="fig-2"
                                        )
                                        storage_context = StorageContext.from_defaults(vector_store=vector_store)
                                        VectorStoreIndex.from_documents([scenario_doc], storage_context=storage_context)

                                        st.success("✅ Image processed and saved to fig-2 vector database!")
                                        st.rerun()

                                    except Exception as e:
                                        st.error(f"Error processing image: {str(e)}")

                        st.markdown("---")

                        # OUTPUT BOX
                        st.markdown("##### OUTPUT BOX")
                        st.caption("The answer in the output box is editable. Using the cursor, the user can add or edit the responses by typing.")

                        scenario_output = st.text_area(
                            "Scenario Output",
                            value=st.session_state.get(f'scenario_output_{current_scenario}', ''),
                            height=350,
                            key=f"scenario_output_box_{current_scenario}",
                            label_visibility="collapsed",
                            placeholder="Generated scenario description will appear here. You can edit before saving."
                        )

                        # Update session state
                        st.session_state[f'scenario_output_{current_scenario}'] = scenario_output

                        # Save and Proceed buttons
                        save_col, proceed_col = st.columns(2)

                        with save_col:
                            if st.button("💾 Save", type="primary", key=f"save_scenario_{current_scenario}"):
                                if not scenario_output.strip():
                                    st.error("⚠️ Output box is empty")
                                else:
                                    with st.spinner("Saving scenario to fig-2 vector DB and SQLite..."):
                                        try:
                                            # Save to fig-2 vector database
                                            from llama_index.core import Document, VectorStoreIndex, StorageContext
                                            from llama_index.vector_stores.pinecone import PineconeVectorStore

                                            scenario_doc = Document(
                                                text=f"Scenario Diagram {current_scenario} Description:\n{scenario_output}",
                                                metadata={
                                                    "source": f"scenario_{current_scenario}",
                                                    "type": "scenario_description"
                                                }
                                            )

                                            vector_store = PineconeVectorStore(
                                                pinecone_index=st.session_state['pinecone_index'],
                                                namespace="fig-2"
                                            )
                                            storage_context = StorageContext.from_defaults(vector_store=vector_store)
                                            VectorStoreIndex.from_documents([scenario_doc], storage_context=storage_context)

                                            # Save to SQLite
                                            save_section_and_notify_memori(
                                                f'scenario_diagram_{current_scenario}',
                                                st.session_state.get('title_of_invention', ''),
                                                f"Scenario Diagram {current_scenario}",
                                                scenario_output
                                            )

                                            # Store in scenario_outputs
                                            st.session_state['scenario_outputs'][current_scenario] = scenario_output

                                            st.success(f"✅ Scenario {current_scenario} saved!")

                                        except Exception as e:
                                            st.error(f"❌ Error saving: {str(e)}")

                        with proceed_col:
                            if st.button("➡️ PROCEED", key=f"proceed_scenario_{current_scenario}"):
                                if scenario_output.strip():
                                    # Move to next scenario
                                    st.session_state['current_scenario_index'] += 1
                                    st.session_state['scenario_diagrams_count'] += 1
                                    st.success(f"✅ Moving to Scenario {current_scenario + 1}")
                                    st.rerun()
                                else:
                                    st.warning("⚠️ Save content first before proceeding")

                    with col_right:
                        st.markdown("##### SYSTEM PROMPT:")
                        default_system_prompt = f"""You are an expert patent writer. Generate a detailed description for Scenario Diagram {current_scenario}.

Using context from:
1. Memori (session memory)
2. Patent claims database
3. Figure 2 vector database (all enabled claim features)
4. General documents

The scenario diagram shows a specific use case or application of the invention. Describe:
- The actors/components involved
- The sequence of operations
- How this scenario relates to the patent claims
- Technical details of the implementation"""

                        system_prompt = st.text_area(
                            "System Prompt",
                            value=default_system_prompt,
                            height=200,
                            key=f"scenario_system_prompt_{current_scenario}",
                            label_visibility="collapsed"
                        )

                        st.markdown("##### QUERY INPUT:")
                        st.caption("Change in query input changes the answer in the output box.")

                        query_input = st.text_area(
                            "Query Input",
                            placeholder=f"Describe Scenario Diagram {current_scenario}...",
                            height=150,
                            key=f"scenario_query_{current_scenario}",
                            label_visibility="collapsed"
                        )

                        # Generate button
                        if st.button("🔄 Generate Description", type="primary", key=f"generate_scenario_{current_scenario}"):
                            if not query_input:
                                st.error("⚠️ Please enter a query")
                            else:
                                with st.spinner(f"Generating scenario {current_scenario} description..."):
                                    try:
                                        context_parts = []

                                        # Get vision extraction if available
                                        if f'scenario_vision_{current_scenario}' in st.session_state:
                                            context_parts.append(f"=== SCENARIO IMAGE ANALYSIS ===\n{st.session_state[f'scenario_vision_{current_scenario}']}")

                                        # Get from fig-2 namespace (includes all enabled features)
                                        if st.session_state.get('fig2_index'):
                                            fig2_retriever = st.session_state['fig2_index'].as_retriever(similarity_top_k=5)
                                            fig2_nodes = fig2_retriever.retrieve(query_input)
                                            fig2_context = "\n".join([node.text for node in fig2_nodes])
                                            context_parts.append(f"=== FIG-2 CONTEXT (Enabled Features) ===\n{fig2_context}")

                                        # Get from general-docs
                                        if st.session_state['index']:
                                            general_retriever = st.session_state['index'].as_retriever(similarity_top_k=3)
                                            general_nodes = general_retriever.retrieve(query_input)
                                            general_context = "\n".join([node.text for node in general_nodes])
                                            context_parts.append(f"=== GENERAL-DOCS CONTEXT ===\n{general_context}")

                                        # Get enabled features summary
                                        if st.session_state.get('enabled_features'):
                                            enabled_summary = "\n".join([f"{fid}: {ftext[:100]}..." for fid, ftext in st.session_state['enabled_features'].items()])
                                            context_parts.append(f"=== ENABLED CLAIM FEATURES ===\n{enabled_summary}")

                                        full_context = "\n\n".join(context_parts)

                                        response = st.session_state['anthropic_client'].messages.create(
                                            model="claude-sonnet-4-20250514",
                                            max_tokens=4096,
                                            system=system_prompt + f"\n\nCONTEXT:\n{full_context}",
                                            messages=[{
                                                "role": "user",
                                                "content": f"Generate description for Scenario Diagram {current_scenario}:\n\n{query_input}"
                                            }]
                                        )

                                        output = response.content[0].text.strip()
                                        st.session_state[f'scenario_output_{current_scenario}'] = output
                                        st.rerun()

                                    except Exception as e:
                                        st.error(f"Error generating: {str(e)}")

                    # Show previously saved scenarios
                    if st.session_state['scenario_outputs']:
                        st.markdown("---")
                        st.markdown("### Previously Saved Scenarios")
                        with st.expander(f"View {len(st.session_state['scenario_outputs'])} saved scenarios", expanded=False):
                            for scenario_num, scenario_text in st.session_state['scenario_outputs'].items():
                                st.markdown(f"**Scenario {scenario_num}:** {scenario_text[:300]}...")

                    # Complete Patent Document button
                    st.markdown("---")
                    if st.session_state['scenario_outputs']:
                        if st.button("🎉 Complete Patent Document", type="primary", key="complete_patent"):
                            st.balloons()
                            st.success("🎊 Congratulations! Patent document generation completed!")
                            st.markdown(f"""
                            ### Summary:
                            - **Claim Features Enabled:** {len(st.session_state.get('enabled_features', {}))}
                            - **Scenario Diagrams Created:** {len(st.session_state['scenario_outputs'])}
                            - All content saved to fig-2 vector database and SQLite
                            """)


if __name__ == "__main__":
    main()