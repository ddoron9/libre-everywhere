"""
Simple file validation for security.
"""

import os
import mimetypes
from fastapi import HTTPException

# 설정
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 100 * 1024 * 1024))  # 100MB
ALLOWED_EXTENSIONS = {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.hwp', '.mht', '.rtf', '.odt'}
ALLOWED_MIME_TYPES = {
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/x-hwp',
    'message/rfc822',
    'application/rtf',
    'application/vnd.oasis.opendocument.text',
    'text/plain',
    'application/octet-stream',
}

def validate_file(file_content: bytes, filename: str) -> None:
    """파일 검증 (크기, 확장자, MIME 타입)"""
    
    # 1. 파일 크기 검증
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # 2. 파일 확장자 검증
    file_ext = os.path.splitext(filename.lower())[1]
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{file_ext}' not allowed. Allowed: {list(ALLOWED_EXTENSIONS)}"
        )
    
    # 3. MIME 타입 검증 (기본적인 검증)
    try:
        import magic
        mime_type = magic.from_buffer(file_content, mime=True)
        if mime_type not in ALLOWED_MIME_TYPES:
            # 경고만 하고 차단하지는 않음 (너무 엄격하면 정상 파일도 차단)
            print(f"Warning: Potentially unsupported MIME type: {mime_type}")
    except ImportError:
        # python-magic이 없으면 기본 검증만
        mime_type, _ = mimetypes.guess_type(filename)
        print(f"Basic MIME type check: {mime_type}")
