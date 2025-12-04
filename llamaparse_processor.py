"""
LlamaParse Document Processor

Enhanced PDF and document parsing using LlamaParse for better extraction of:
- Complex tables
- Charts and graphs (converted to data tables)
- Multi-column layouts
- Images with context

Falls back to existing PyMuPDF processing if LlamaParse is unavailable.
"""

import os
from typing import List, Optional
from llama_index.core import Document

# Try to import LlamaParse
try:
    from llama_parse import LlamaParse
    LLAMAPARSE_AVAILABLE = True
except ImportError:
    LLAMAPARSE_AVAILABLE = False
    print("LlamaParse not installed - will use PyMuPDF fallback for PDFs")


def is_llamaparse_available() -> bool:
    """Check if LlamaParse is available and configured."""
    if not LLAMAPARSE_AVAILABLE:
        return False

    api_key = os.environ.get("LLAMA_CLOUD_API_KEY")
    if not api_key:
        print("LLAMA_CLOUD_API_KEY not set - will use PyMuPDF fallback for PDFs")
        return False

    return True


def get_llamaparse_parser() -> Optional[LlamaParse]:
    """
    Initialize and return a LlamaParse parser with optimal settings.

    Returns:
        LlamaParse instance or None if unavailable
    """
    if not is_llamaparse_available():
        return None

    try:
        parser = LlamaParse(
            api_key=os.environ.get("LLAMA_CLOUD_API_KEY"),
            result_type="markdown",  # Output as markdown for easy processing

            # Enable advanced features for better extraction
            extract_charts=True,  # Extract data from charts/graphs

            # Auto-mode: Only use premium parsing when needed (cost optimization)
            auto_mode=True,
            auto_mode_trigger_on_image_in_page=True,
            auto_mode_trigger_on_table_in_page=True,

            # Additional settings
            verbose=False,
        )
        return parser
    except Exception as e:
        print(f"Failed to initialize LlamaParse: {e}")
        return None


def parse_pdf_with_llamaparse(file_path: str) -> List[Document]:
    """
    Parse a PDF file using LlamaParse.

    Args:
        file_path: Path to the PDF file

    Returns:
        List of LlamaIndex Document objects
    """
    parser = get_llamaparse_parser()
    if not parser:
        return []

    try:
        file_name = os.path.basename(file_path)
        extra_info = {"file_name": file_name}

        print(f"LlamaParse: Parsing {file_name}...")

        # Parse the document
        with open(file_path, "rb") as f:
            parsed_documents = parser.load_data(f, extra_info=extra_info)

        # Convert to our Document format with metadata
        documents = []
        for i, doc in enumerate(parsed_documents):
            # LlamaParse returns documents with text content
            text = doc.text if hasattr(doc, 'text') else str(doc)

            # Create document with metadata
            document = Document(
                text=text,
                metadata={
                    "source": f"{file_name}",
                    "type": "pdf",
                    "parser": "llamaparse",
                    "page_num": i,
                    "file_name": file_name
                }
            )
            documents.append(document)

        print(f"LlamaParse: Successfully extracted {len(documents)} document(s) from {file_name}")
        return documents

    except Exception as e:
        print(f"LlamaParse error parsing {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return []


def parse_document_with_llamaparse(file_path: str, file_type: str) -> List[Document]:
    """
    Parse any supported document using LlamaParse.

    Args:
        file_path: Path to the document file
        file_type: File extension (e.g., '.pdf', '.docx')

    Returns:
        List of LlamaIndex Document objects
    """
    # LlamaParse primarily excels at PDF parsing
    # For other formats, it can still be used but may not provide significant benefits

    if file_type.lower() == '.pdf':
        return parse_pdf_with_llamaparse(file_path)

    # For DOCX files, LlamaParse can also be used
    if file_type.lower() in ['.docx', '.doc']:
        return parse_pdf_with_llamaparse(file_path)  # LlamaParse handles DOCX too

    # For other types, return empty (caller should use existing processors)
    return []


def parse_uploaded_file_with_llamaparse(uploaded_file) -> List[Document]:
    """
    Parse an uploaded Streamlit file using LlamaParse.

    Args:
        uploaded_file: Streamlit UploadedFile object

    Returns:
        List of LlamaIndex Document objects
    """
    if not is_llamaparse_available():
        return []

    parser = get_llamaparse_parser()
    if not parser:
        return []

    try:
        file_name = uploaded_file.name
        file_extension = os.path.splitext(file_name.lower())[1]

        # Only use LlamaParse for PDFs (primary use case)
        if file_extension != '.pdf':
            return []

        extra_info = {"file_name": file_name}

        print(f"LlamaParse: Parsing uploaded file {file_name}...")

        # Read file content
        file_content = uploaded_file.read()
        uploaded_file.seek(0)  # Reset file pointer for potential reuse

        # Save to temp file (LlamaParse works better with file paths)
        temp_dir = os.path.join(os.getcwd(), "vectorstore", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, file_name)

        with open(temp_path, "wb") as f:
            f.write(file_content)

        # Parse using file path
        documents = parse_pdf_with_llamaparse(temp_path)

        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass

        return documents

    except Exception as e:
        print(f"LlamaParse error with uploaded file: {e}")
        import traceback
        traceback.print_exc()
        return []
