import mimetypes
import os
from typing import Optional

from fastapi import Header, HTTPException

from src.logging_config import get_logger

logger = get_logger(__name__)

# API Key Authentication
API_KEY = os.getenv("API_KEY", "your-secret-api-key-change-this")


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """Verify API key from request header."""
    if not x_api_key:
        raise HTTPException(
            status_code=401, detail="API key required. Please provide X-API-Key header."
        )

    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key.")

    return True

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 100 * 1024 * 1024))  # 100MB
ALLOWED_EXTENSIONS = {
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".hwp",
    ".mht",
    ".rtf",
    ".odt",
}
ALLOWED_MIME_TYPES = {
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/x-hwp",
    "message/rfc822",
    "application/rtf",
    "application/vnd.oasis.opendocument.text",
    "text/plain",
    "application/octet-stream",
}


def validate_uploaded_file(file_content: bytes, filename: str) -> None:
    """Validate uploaded file (size, extension, MIME type)."""

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    file_ext = os.path.splitext(filename.lower())[1]
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{file_ext}' not allowed. Allowed: {list(ALLOWED_EXTENSIONS)}",
        )

    try:
        import magic

        mime_type = magic.from_buffer(file_content, mime=True)
        if mime_type not in ALLOWED_MIME_TYPES:
            logger.warning(f"Potentially unsupported MIME type: {mime_type}")
    except ImportError:
        mime_type, _ = mimetypes.guess_type(filename)
        logger.warning(f"Basic MIME type check: {mime_type}")
