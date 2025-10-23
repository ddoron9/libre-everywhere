"""
Configuration for file conversion mappings and settings.
"""

# Default conversion mappings
# Key: input extension, Value: list of output extensions
CONVERSION_MAPPINGS = {
    ".doc": ["pdf"],
    # ".docx": ["pdf"],
    ".rtf": ["pdf"],
    ".odt": ["pdf"],
    ".xls": ["xlsx"],
    ".xlsm": ["xlsx"],
    ".ppt": ["pptx"],
    ".hwp": ["pdf"],
    ".mht": ["html"],
}

# Fallback order for each conversion type
FALLBACK_ORDER = {
    "doc_to_docx": ["libreoffice", "abiword"],
    "doc_to_pdf": ["libreoffice", "abiword"],
    "docx_to_pdf": ["libreoffice", "abiword"],
    "rtf_to_pdf": ["libreoffice", "abiword"],
    "odt_to_pdf": ["libreoffice", "abiword"],
    "xls_to_xlsx": ["libreoffice", "pandas"],
    "xlsm_to_xlsx": ["libreoffice", "pandas"],
    "ppt_to_pptx": ["libreoffice"],
    "hwp_to_html": ["hwp5html"],
    "hwp_to_pdf": ["weasyprint"],
    "mht_to_html": ["mhtml_extractor", "email_parser"],
}

# Test file configurations
TEST_FILES = {
    "doc": "test/data/test.doc",
    "xls": "test/data/test.xls",
    "ppt": "test/data/test.ppt",
    "hwp": "test/data/test.hwp",
    "mht": "test/data/test.mht",
}

# Output directory for converted files
OUTPUT_DIR = "converted_files"

# Temporary directory for test files
TEMP_DIR = "temp_test_files"

def get_output_extensions(input_ext: str) -> list:
    """
    Get the list of output extensions for a given input extension.
    
    Args:
        input_ext: Input file extension (with or without dot)
        
    Returns:
        List of output extensions, defaults to ["pdf"] if not found
    """
    if not input_ext.startswith('.'):
        input_ext = '.' + input_ext
    
    return CONVERSION_MAPPINGS.get(input_ext.lower(), ["pdf"])

def get_fallback_methods(conversion_type: str) -> list:
    """
    Get the fallback methods for a specific conversion type.
    
    Args:
        conversion_type: Type of conversion (e.g., "doc_to_docx")
        
    Returns:
        List of fallback methods in order of preference
    """
    return FALLBACK_ORDER.get(conversion_type, [])

def should_convert_to_pdf_only(input_ext: str) -> bool:
    """
    Check if the input extension should only convert to PDF.
    
    Args:
        input_ext: Input file extension
        
    Returns:
        True if should only convert to PDF, False otherwise
    """
    if not input_ext.startswith('.'):
        input_ext = '.' + input_ext
    
    output_exts = get_output_extensions(input_ext)
    return len(output_exts) == 1 and output_exts[0] == "pdf"

def get_conversion_config():
    """
    Get the complete conversion configuration.
    
    Returns:
        Dictionary with all configuration settings
    """
    return {
        "mappings": CONVERSION_MAPPINGS,
        "fallbacks": FALLBACK_ORDER,
        "test_files": TEST_FILES,
        "output_dir": OUTPUT_DIR,
        "temp_dir": TEMP_DIR,
    }
