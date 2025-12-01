# This file contains the TAB INTERFACE code to replace col2 section in app.py
# Lines 473-667 will be replaced with this code

# Place this code starting at line 473 in app.py:

"""
    with col2:
        if st.session_state['index'] is not None:
            # Get retriever for all tabs
            retriever = st.session_state['index'].as_retriever(similarity_top_k=5)

            # Create tab interface
            tab_names = [
                "1️⃣ BACKGROUND",
                "2️⃣ SUMMARY",
                "3️⃣ BRIEF DESCRIPTION OF DRAWINGS",
                "4️⃣ TECHNICAL PROBLEMS",
                "5️⃣ TECHNICAL ADVANTAGES",
                "6️⃣ SUMMARY PARAPHRASE",
                "7️⃣ FIGURE 2 INTRODUCTION",
                "8️⃣ FIGURE 2 CLAIM ENABLEMENT",
                "9️⃣ SCENARIO DIAGRAMS"
            ]

            tabs = st.tabs(tab_names)

            # ================================================================
            # TAB 0: BACKGROUND
            # ================================================================
            with tabs[0]:
                st.markdown("### Background Section")

                section_type = 'background'
                section_key = f'{section_type}_output'

                # System Prompt
                default_prompt = "You are an expert technical writer. Based on the provided context, generate a comprehensive background section that explains the technical context, prior art, and motivation for this invention."
                system_prompt = st.text_area(
                    "System Prompt",
                    value=default_prompt,
                    height=150,
                    key=f"{section_type}_system_prompt",
                    help="Define how the LLM should behave"
                )

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
                        if st.button("💾 Save Background", type="primary", use_container_width=True, key=f"{section_type}_save"):
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
                            if st.button("➡️ Proceed to Summary", use_container_width=True, key=f"{section_type}_proceed"):
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
            # TAB 1: SUMMARY
            # ================================================================
            with tabs[1]:
                if not st.session_state['tabs_unlocked']['summary']:
                    st.warning("⚠️ Complete Background section first to unlock this tab")
                else:
                    st.markdown("### Summary Section")
                    section_type = 'summary'
                    section_key = f'{section_type}_output'

                    # System Prompt
                    default_prompt = "You are an expert patent writer. Generate a concise summary section that provides an overview of the invention, its key features, and advantages."
                    system_prompt = st.text_area(
                        "System Prompt",
                        value=default_prompt,
                        height=150,
                        key=f"{section_type}_system_prompt"
                    )

                    # Query Input
                    query = st.text_area(
                        "Query Input",
                        placeholder="Enter your query to generate summary...",
                        height=100,
                        key=f"{section_type}_query"
                    )

                    # Generate Button
                    if st.button("Generate Summary", type="primary", key=f"{section_type}_generate"):
                        if not query:
                            st.error("⚠️ Please enter a query")
                        else:
                            with st.spinner("Generating summary..."):
                                try:
                                    output = generate_section_content(section_type, system_prompt, query, retriever)
                                    st.session_state['current_section_output'][section_key] = {
                                        "query": query,
                                        "output": output
                                    }
                                    st.success("✅ Summary generated!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")

                    # Display Generated Content
                    if section_key in st.session_state['current_section_output']:
                        st.markdown("---")
                        st.markdown("### Generated Summary")
                        st.markdown(st.session_state['current_section_output'][section_key]['output'])

                        # Save, Skip, Proceed Buttons
                        col_save, col_skip, col_proceed = st.columns(3)

                        with col_save:
                            if st.button("💾 Save", type="primary", use_container_width=True, key=f"{section_type}_save"):
                                title = st.session_state.get('title_of_invention', 'Summary Section')
                                query_text = st.session_state['current_section_output'][section_key]['query']
                                content = st.session_state['current_section_output'][section_key]['output']

                                try:
                                    section_id = save_section_and_notify_memori(section_type, title, query_text, content)
                                    st.success(f"✅ Summary saved! (ID: {section_id})")
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")

                        with col_skip:
                            if st.button("⏭️ Skip", use_container_width=True, key=f"{section_type}_skip"):
                                title = st.session_state.get('title_of_invention', 'Summary Section')
                                save_section_and_notify_memori(section_type, title, "", "", skipped=True)
                                unlock_next_tab('summary')
                                st.session_state['current_section_output'].pop(section_key, None)
                                st.info("⏭️ Summary skipped. Drawings tab unlocked!")
                                st.rerun()

                        with col_proceed:
                            summary_saved = st.session_state['patent_sections_db'].get_section('summary') is not None

                            if summary_saved:
                                if st.button("➡️ Proceed", use_container_width=True, key=f"{section_type}_proceed"):
                                    unlock_next_tab('summary')
                                    st.session_state['current_section_output'].pop(section_key, None)
                                    st.success("✅ Drawings tab unlocked!")
                                    st.rerun()
                            else:
                                st.info("💾 Save or Skip first")

                    # Show Saved Summary
                    saved_section = st.session_state['patent_sections_db'].get_section('summary')
                    if saved_section:
                        st.markdown("---")
                        if saved_section['skipped']:
                            st.markdown("### ⏭️ Summary Section (Skipped)")
                        else:
                            st.markdown("### Saved Summary")
                            with st.expander(f"View Saved Summary (ID: {saved_section['id']})"):
                                for para_num, para_text in saved_section['paragraphs']:
                                    st.markdown(f"**{para_num}** {para_text}\n")

            # ================================================================
            # TAB 2: BRIEF DESCRIPTION OF DRAWINGS
            # ================================================================
            with tabs[2]:
                if not st.session_state['tabs_unlocked']['drawings']:
                    st.warning("⚠️ Complete Summary section first to unlock this tab")
                else:
                    st.markdown("### Brief Description of Drawings")
                    section_type = 'drawings'
                    section_key = f'{section_type}_output'

                    # [Similar structure to Summary tab - with Save, Skip, Proceed]
                    # System Prompt
                    default_prompt = "You are an expert patent writer. Generate a brief description of the drawings/figures that will be included in the patent. Describe each figure concisely."
                    system_prompt = st.text_area("System Prompt", value=default_prompt, height=150, key=f"{section_type}_system_prompt")

                    query = st.text_area("Query Input", placeholder="Describe the figures...", height=100, key=f"{section_type}_query")

                    if st.button("Generate Drawings Description", type="primary", key=f"{section_type}_generate"):
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

                        col_save, col_skip, col_proceed = st.columns(3)

                        with col_save:
                            if st.button("💾 Save", type="primary", use_container_width=True, key=f"{section_type}_save"):
                                title = st.session_state.get('title_of_invention', 'Drawings Section')
                                save_section_and_notify_memori(section_type, title, st.session_state['current_section_output'][section_key]['query'], st.session_state['current_section_output'][section_key]['output'])
                                st.success("✅ Saved!")

                        with col_skip:
                            if st.button("⏭️ Skip", use_container_width=True, key=f"{section_type}_skip"):
                                save_section_and_notify_memori(section_type, "", "", "", skipped=True)
                                unlock_next_tab('drawings')
                                st.session_state['current_section_output'].pop(section_key, None)
                                st.rerun()

                        with col_proceed:
                            if st.session_state['patent_sections_db'].get_section('drawings'):
                                if st.button("➡️ Proceed", use_container_width=True, key=f"{section_type}_proceed"):
                                    unlock_next_tab('drawings')
                                    st.session_state['current_section_output'].pop(section_key, None)
                                    st.rerun()

            # ================================================================
            # TABS 3-8: TECHNICAL PROBLEMS, ADVANTAGES, etc. (NO SKIP)
            # ================================================================

            # TAB 3: TECHNICAL PROBLEMS
            with tabs[3]:
                if not st.session_state['tabs_unlocked']['technical_problems']:
                    st.warning("⚠️ Complete Drawings section first")
                else:
                    section_type = 'technical_problems'
                    section_key = f'{section_type}_output'
                    st.markdown("### Technical Problems")

                    default_prompt = "You are an expert patent writer. Identify and describe the technical problems that this invention solves. Be specific and detailed."
                    system_prompt = st.text_area("System Prompt", value=default_prompt, height=150, key=f"{section_type}_system_prompt")
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
                            if st.button("💾 Save", type="primary", use_container_width=True, key=f"{section_type}_save"):
                                title = st.session_state.get('title_of_invention', '')
                                save_section_and_notify_memori(section_type, title, st.session_state['current_section_output'][section_key]['query'], st.session_state['current_section_output'][section_key]['output'])
                                st.success("✅ Saved!")

                        with col_proceed:
                            if st.session_state['patent_sections_db'].get_section('technical_problems'):
                                if st.button("➡️ Proceed", use_container_width=True, key=f"{section_type}_proceed"):
                                    unlock_next_tab('technical_problems')
                                    st.session_state['current_section_output'].pop(section_key, None)
                                    st.rerun()

            # Continue similarly for tabs 4-8...
            # (I'll implement a generic renderer in the actual app.py)

"""

# Note: The above code is approximately 400 lines.
# Tabs 4-8 follow the same pattern as Tab 3 (Technical Problems) - no skip button
# Each subsequent tab should follow this exact structure
