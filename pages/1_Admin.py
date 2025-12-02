"""
Admin Dashboard Page for Streamlit Multi-Page App
"""

import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from admin_config import AdminConfigDB

# Page config
st.set_page_config(
    page_title="Admin Dashboard - Patent Generator",
    page_icon="🔐",
    layout="wide"
)

# Initialize admin config database
if 'admin_db' not in st.session_state:
    st.session_state['admin_db'] = AdminConfigDB()

# Initialize session state for admin login
if 'admin_logged_in' not in st.session_state:
    st.session_state['admin_logged_in'] = False
if 'admin_email' not in st.session_state:
    st.session_state['admin_email'] = None


def show_login_page():
    """Display admin login page"""

    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    }
    .login-title {
        color: white;
        text-align: center;
        font-size: 28px;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("## 🔐 Admin Login")
        st.markdown("---")
        st.markdown("### Patent Document Generator")
        st.markdown("Enter your admin credentials to access the dashboard.")

        with st.form("admin_login_form"):
            email = st.text_input("📧 Email", placeholder="Enter admin email")
            password = st.text_input("🔑 Password", type="password", placeholder="Enter password")

            submit = st.form_submit_button("🚀 Login")

            if submit:
                if not email or not password:
                    st.error("⚠️ Please enter both email and password")
                else:
                    if st.session_state['admin_db'].verify_admin(email, password):
                        st.session_state['admin_logged_in'] = True
                        st.session_state['admin_email'] = email
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials. Please try again.")

        st.markdown("---")
        st.markdown("*Only authorized administrators can access this page.*")


def show_admin_dashboard():
    """Display admin dashboard with prompt management"""

    # Sidebar
    with st.sidebar:
        st.markdown("## 🔐 Admin Panel")
        st.markdown(f"**Logged in as:** {st.session_state['admin_email']}")
        st.markdown("---")

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state['admin_logged_in'] = False
            st.session_state['admin_email'] = None
            st.rerun()

        st.markdown("---")
        st.markdown("### Navigation")
        page = st.radio(
            "Select Page",
            ["📝 Manage Prompts", "➕ Add New Prompt", "📊 Overview"],
            label_visibility="collapsed"
        )

    # Main content
    st.markdown("# 🛠️ Admin Dashboard")
    st.markdown("### Patent Document Generator - Prompt Management")
    st.markdown("---")

    if page == "📝 Manage Prompts":
        manage_prompts_page()
    elif page == "➕ Add New Prompt":
        add_prompt_page()
    else:
        overview_page()


def manage_prompts_page():
    """Page to view and edit existing prompts"""

    st.markdown("## 📝 Manage System Prompts")
    st.info("Edit the system prompts used throughout the patent document generation process.")

    prompts = st.session_state['admin_db'].get_all_prompts()

    if not prompts:
        st.warning("No prompts found in the database. Add some prompts first!")
        return

    # Create tabs for each prompt section
    prompt_tabs = st.tabs([p['section_name'] for p in prompts])

    for i, prompt_data in enumerate(prompts):
        with prompt_tabs[i]:
            st.markdown(f"### {prompt_data['section_name']}")
            st.markdown(f"**Section Key:** `{prompt_data['section_key']}`")
            st.markdown(f"**Description:** {prompt_data['description']}")
            st.markdown(f"**Last Updated:** {prompt_data['updated_at']} by {prompt_data['updated_by']}")

            st.markdown("---")

            # Editable prompt text
            edited_prompt = st.text_area(
                "System Prompt",
                value=prompt_data['prompt_text'],
                height=400,
                key=f"edit_prompt_{prompt_data['section_key']}"
            )

            col1, col2 = st.columns([1, 4])

            with col1:
                if st.button("💾 Save Changes", key=f"save_{prompt_data['section_key']}", type="primary"):
                    if edited_prompt != prompt_data['prompt_text']:
                        success = st.session_state['admin_db'].update_prompt(
                            prompt_data['section_key'],
                            edited_prompt,
                            st.session_state['admin_email']
                        )
                        if success:
                            st.success("✅ Prompt updated successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to update prompt")
                    else:
                        st.info("No changes detected")


def add_prompt_page():
    """Page to add new custom prompts"""

    st.markdown("## ➕ Add New System Prompt")
    st.info("Create a new custom prompt for additional sections.")

    with st.form("add_prompt_form"):
        section_key = st.text_input(
            "Section Key (unique identifier)",
            placeholder="e.g., custom_section_1",
            help="Use lowercase with underscores, no spaces"
        )

        section_name = st.text_input(
            "Section Name (display name)",
            placeholder="e.g., Custom Section"
        )

        description = st.text_area(
            "Description",
            placeholder="Describe what this prompt is used for...",
            height=100
        )

        prompt_text = st.text_area(
            "Prompt Text",
            placeholder="Enter the system prompt...",
            height=400
        )

        submitted = st.form_submit_button("➕ Add Prompt", type="primary")

        if submitted:
            if not section_key or not section_name or not prompt_text:
                st.error("⚠️ Please fill in all required fields")
            elif " " in section_key:
                st.error("⚠️ Section Key cannot contain spaces")
            else:
                success = st.session_state['admin_db'].add_prompt(
                    section_key,
                    section_name,
                    prompt_text,
                    description,
                    st.session_state['admin_email']
                )
                if success:
                    st.success(f"✅ Prompt '{section_name}' added successfully!")
                    st.balloons()
                else:
                    st.error(f"❌ Failed to add prompt. Key may already exist.")


def overview_page():
    """Overview page with statistics"""

    st.markdown("## 📊 System Overview")

    prompts = st.session_state['admin_db'].get_all_prompts()

    # Stats
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Prompts", len(prompts))

    with col2:
        st.metric("Admin Email", st.session_state['admin_email'])

    with col3:
        st.metric("Database", "Turso Cloud" if os.environ.get("TURSO_DATABASE_URL") else "Local SQLite")

    st.markdown("---")

    # Prompts summary table
    st.markdown("### Prompts Summary")

    if prompts:
        import pandas as pd
        df = pd.DataFrame([
            {
                "Section": p['section_name'],
                "Key": p['section_key'],
                "Description": p['description'][:50] + "..." if p['description'] and len(p['description']) > 50 else (p['description'] or ""),
                "Last Updated": p['updated_at'],
                "Updated By": p['updated_by']
            }
            for p in prompts
        ])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No prompts configured yet.")


# Main execution
if not st.session_state['admin_logged_in']:
    show_login_page()
else:
    show_admin_dashboard()
