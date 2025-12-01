"""
Patent Context Manager - Maintains session-wide awareness for antecedent basis tracking.

This module ensures that:
1. All previously written sections are available as context
2. Antecedent basis is maintained (first mention vs subsequent mentions with "the")
3. Technical terms introduced in earlier sections are properly referenced in later sections
4. The entire patent drafting session maintains consistency
"""

class PatentContextManager:
    """
    Manages patent drafting context across all sections.

    Ensures antecedent basis compliance:
    - First mention: "application containers"
    - Subsequent mentions: "the application containers"
    """

    def __init__(self, patent_sections_db, patent_db):
        """
        Initialize with database references.

        Args:
            patent_sections_db: PatentSectionsDatabase instance
            patent_db: PatentClaimsDatabase instance
        """
        self.patent_sections_db = patent_sections_db
        self.patent_db = patent_db
        self.session_context = {}
        self.introduced_terms = set()  # Track terms that have been introduced

    def get_full_session_context(self):
        """
        Build complete session context from all saved sections.

        Returns:
            dict with all section contents and metadata
        """
        context = {
            'title': None,
            'claims': [],
            'sections': {},
            'section_order': [],
            'introduced_terms': list(self.introduced_terms)
        }

        # Get title
        if self.patent_db:
            # Title is usually stored in session_state, but we can get claim 1 as reference
            claims = self.patent_db.get_all_claims()
            if claims:
                context['claims'] = [(num, text) for num, text in claims]

        # Section order for patent document
        section_types = [
            'background',
            'summary',
            'drawings',
            'technical_problems',
            'technical_advantages',
            'summary_paraphrase',
            'figure2_intro',
            'sequencing',
            'figure2_enablement',
            'scenario_diagrams'
        ]

        # Load each section if it exists
        for section_type in section_types:
            section = self.patent_sections_db.get_section(section_type)
            if section and not section.get('skipped', False):
                content_text = ""
                if section.get('paragraphs'):
                    for para_num, para_text in section['paragraphs']:
                        content_text += f"{para_num}: {para_text}\n"

                context['sections'][section_type] = {
                    'id': section.get('id'),
                    'title': section.get('title', ''),
                    'content': content_text,
                    'query': section.get('query', '')
                }
                context['section_order'].append(section_type)

        # Also check for dynamic sections (enablement_C#F#, scenario_diagram_#)
        # These are stored with generic section types

        return context

    def build_context_prompt(self, current_section_type, title_of_invention=None):
        """
        Build a context prompt that includes all relevant previous sections.

        This ensures antecedent basis is maintained - any term introduced in
        earlier sections should be referenced with "the" in later sections.

        Args:
            current_section_type: The section currently being generated
            title_of_invention: Title of the patent

        Returns:
            str: Context prompt to prepend to system prompt
        """
        context = self.get_full_session_context()

        # Build context string
        context_parts = []

        # Add title
        if title_of_invention:
            context_parts.append(f"**TITLE OF INVENTION:** {title_of_invention}")

        # Add antecedent basis instructions
        context_parts.append("""
**CRITICAL - ANTECEDENT BASIS RULES:**
In patent drafting, antecedent basis must be maintained:
- When a term is FIRST introduced in the document, use it without "the" (e.g., "a processing unit", "application containers")
- When that SAME term appears AGAIN (in the same section OR any later section), use "the" before it (e.g., "the processing unit", "the application containers")
- Review ALL previous sections below to identify terms that have already been introduced
- ANY term that appears in the sections below has ALREADY been introduced and MUST use "the" when referenced again

This is a MANDATORY patent drafting requirement for proper claim support.
""")

        # Add previous sections
        if context['sections']:
            context_parts.append("\n**PREVIOUSLY WRITTEN SECTIONS (for context and antecedent basis):**\n")
            context_parts.append("=" * 60)

            for section_type in context['section_order']:
                if section_type == current_section_type:
                    break  # Don't include current or later sections

                section_data = context['sections'].get(section_type)
                if section_data:
                    section_name = section_type.replace('_', ' ').title()
                    context_parts.append(f"\n### {section_name} Section ###")
                    context_parts.append(section_data['content'])
                    context_parts.append("-" * 40)

        # Add claims context if available
        if context['claims']:
            context_parts.append("\n**PATENT CLAIMS (for reference):**")
            for claim_num, claim_text in context['claims'][:3]:  # First 3 claims
                context_parts.append(f"\nClaim {claim_num}: {claim_text[:500]}...")

        return "\n".join(context_parts)

    def get_section_specific_context(self, section_type, title_of_invention=None):
        """
        Get context specifically tailored for a section type.

        Args:
            section_type: Type of section being generated
            title_of_invention: Title of the patent

        Returns:
            str: Section-specific context
        """
        base_context = self.build_context_prompt(section_type, title_of_invention)

        # Add section-specific instructions
        section_instructions = {
            'technical_advantages': """
**SECTION-SPECIFIC INSTRUCTION:**
You are writing the Technical Advantages section.
- Review the Technical Problems section above carefully
- ANY term mentioned in Technical Problems MUST use "the" when referenced here
- Example: If Technical Problems introduced "application containers", write "the application containers" here
- Maintain consistency with all previously established terminology
""",
            'figure2_intro': """
**SECTION-SPECIFIC INSTRUCTION:**
You are writing the Figure 2 Introduction.
- All technical terms from Background, Summary, Technical Problems, and Technical Advantages have been established
- Use "the" before any previously introduced terms
- Reference components with their established names
""",
            'figure2_enablement': """
**SECTION-SPECIFIC INSTRUCTION:**
You are writing claim feature enablement descriptions.
- All sections above provide the established terminology
- Maintain antecedent basis with all introduced terms
- Connect claim features to Figure 2 components using established names
""",
            'scenario_diagrams': """
**SECTION-SPECIFIC INSTRUCTION:**
You are writing scenario diagram descriptions.
- The entire patent context is available above
- All technical terms have been established in previous sections
- Use "the" for all previously introduced terms
- Maintain consistency with Figure 2 component naming
"""
        }

        specific_instruction = section_instructions.get(section_type, "")

        return base_context + specific_instruction

    def register_section_completion(self, section_type, content):
        """
        Register that a section has been completed.
        Updates the introduced terms tracker.

        Args:
            section_type: Type of section completed
            content: Content of the completed section
        """
        # Extract potential technical terms (simplified - could be enhanced with NLP)
        # For now, just mark the section as complete
        self.session_context[section_type] = content

    def get_context_summary(self):
        """
        Get a brief summary of what context is available.

        Returns:
            dict: Summary of available context
        """
        context = self.get_full_session_context()
        return {
            'sections_completed': list(context['sections'].keys()),
            'claims_available': len(context['claims']),
            'has_title': context['title'] is not None
        }


def build_enhanced_system_prompt(admin_prompt, context_manager, section_type, title_of_invention=None):
    """
    Build an enhanced system prompt that includes:
    1. Admin-configured prompt
    2. Full session context for antecedent basis

    Args:
        admin_prompt: The admin-configured system prompt
        context_manager: PatentContextManager instance
        section_type: Current section type
        title_of_invention: Title of the patent

    Returns:
        str: Enhanced system prompt with context
    """
    # Get session context
    session_context = context_manager.get_section_specific_context(
        section_type,
        title_of_invention
    )

    # Combine: Context first, then admin prompt
    enhanced_prompt = f"""
{session_context}

{"=" * 60}
**GENERATION INSTRUCTIONS:**
{"=" * 60}

{admin_prompt}
"""

    return enhanced_prompt
