"""
Admin Dashboard for Patent Document Generator
Allows admin to manage system prompts
"""

import streamlit as st
from admin_config import AdminConfigDB

def run_admin_dashboard():
    """Main admin dashboard page"""

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

    # Show login or dashboard based on authentication state
    if not st.session_state['admin_logged_in']:
        show_login_page()
    else:
        show_admin_dashboard()


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

        if st.button("🚪 Logout"):
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
    st.info("Edit the system prompts used throughout the patent document generation process. Changes will be reflected immediately for all users.")

    prompts = st.session_state['admin_db'].get_all_prompts()

    if not prompts:
        st.warning("No prompts found in the database.")
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

            with col2:
                if st.button("🔄 Reset to Default", key=f"reset_{prompt_data['section_key']}"):
                    st.warning("⚠️ This will reset the prompt to its default value. This action cannot be undone.")

            st.markdown("---")
            st.markdown("**Available Placeholders:**")
            st.code("""
{context} - Retrieved context from documents
{title} - Title of the invention
{independent_claim} - The independent claim text
{technical_problems} - Technical problems content
{vision_analysis} - Claude Vision analysis results
{fig2_context} - Figure 2 related context
{additional_context} - Additional retrieved context
{claim_feature} - Current claim feature text
{feature_id} - Current feature ID (e.g., C1F1)
{scenario_number} - Current scenario number
{num_figures} - Number of figures
            """)


def add_prompt_page():
    """Page to add new custom prompts"""

    st.markdown("## ➕ Add New System Prompt")
    st.info("Create a new custom prompt for additional sections or specialized use cases.")

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
            placeholder="Enter the system prompt...\n\nYou can use placeholders like {context}, {title}, etc.",
            height=400
        )

        submitted = st.form_submit_button("➕ Add Prompt", type="primary")

        if submitted:
            if not section_key or not section_name or not prompt_text:
                st.error("⚠️ Please fill in all required fields (Section Key, Section Name, Prompt Text)")
            elif " " in section_key:
                st.error("⚠️ Section Key cannot contain spaces. Use underscores instead.")
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
                    st.error(f"❌ Failed to add prompt. Section key '{section_key}' may already exist.")


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
        st.metric("Database", "admin_config.db")

    st.markdown("---")

    # Prompts summary table
    st.markdown("### Prompts Summary")

    if prompts:
        import pandas as pd
        df = pd.DataFrame([
            {
                "Section": p['section_name'],
                "Key": p['section_key'],
                "Description": p['description'][:50] + "..." if len(p['description']) > 50 else p['description'],
                "Last Updated": p['updated_at'],
                "Updated By": p['updated_by']
            }
            for p in prompts
        ])
        st.dataframe(df)
    else:
        st.info("No prompts configured yet.")

    st.markdown("---")

    # Quick links
    st.markdown("### Quick Actions")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Manage Prompts**
        - Edit existing system prompts
        - Customize AI behavior for each section
        - View prompt placeholders
        """)

    with col2:
        st.markdown("""
        **Add New Prompts**
        - Create custom section prompts
        - Define new AI instructions
        - Extend system functionality
        """)


if __name__ == "__main__":
    run_admin_dashboard()
