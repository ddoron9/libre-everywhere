"""
Simple API key authentication for file conversion API.
"""

import os
from fastapi import HTTPException, Depends, Header
from typing import Optional

API_KEY = os.getenv("API_KEY", "your-secret-api-key-change-this")

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """API 키 검증"""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Please provide X-API-Key header."
        )
    
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key."
        )
    
    return True
