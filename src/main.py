from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import tempfile
import shutil
import mimetypes
from pathlib import Path
import uvicorn
from src.convert import convert_path, convert_any
from src.auth import verify_api_key
from src.validation import validate_file

app = FastAPI(
    title="File Converter API",
    description="파일/폴더를 다양한 형식으로 변환하는 API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

class ConvertRequest(BaseModel):
    input_path: str
    output_path: Optional[str] = None
    convert_to: Optional[str] = None

class ConvertResponse(BaseModel):
    success: bool
    message: str
    converted_files: Dict[str, List[str]]
    total_files: int

@app.get("/")
async def root():
    """API 상태 확인 (인증 불필요)"""
    return {"message": "File Converter API is running", "status": "healthy"}

@app.get("/supported-formats")
async def get_supported_formats(api_key_valid: bool = Depends(verify_api_key)):
    """지원하는 파일 형식 목록 반환"""
    from src.config import CONVERSION_MAPPINGS
    return {
        "supported_formats": CONVERSION_MAPPINGS,
        "description": "Key: 입력 형식, Value: 출력 형식 목록"
    }

@app.post("/convert", response_model=ConvertResponse)
async def convert_files(request: ConvertRequest, api_key_valid: bool = Depends(verify_api_key)):
    """
    파일 또는 폴더를 변환합니다.
    
    - **input_path**: 변환할 파일 또는 폴더 경로
    - **output_path**: 출력 경로 (선택사항, 미입력시 입력 경로와 동일)
    - **convert_to**: 변환할 확장자 (선택사항, 미입력시 기본 변환 규칙 적용)
    """
    try:
        input_path = Path(request.input_path).resolve()
        
        if not input_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"입력 경로를 찾을 수 없습니다: {request.input_path}"
            )
        
        if request.output_path:
            output_path = Path(request.output_path).resolve()
            if not output_path.exists():
                output_path.mkdir(parents=True, exist_ok=True)
        else:
            output_path = input_path.parent if input_path.is_file() else input_path

        original_cwd = os.getcwd()
        
        try:
            os.chdir(output_path)
            
            if input_path.is_file():
                outputs = convert_any(str(input_path), request.convert_to)
                results = {str(input_path): outputs} if outputs else {}
            else:
                results = convert_path(str(input_path))
            
            total_files = len(results)
            
            if total_files == 0:
                return ConvertResponse(
                    success=True,
                    message="변환할 파일이 없습니다.",
                    converted_files={},
                    total_files=0
                )
            
            return ConvertResponse(
                success=True,
                message=f"총 {total_files}개 파일이 성공적으로 변환되었습니다.",
                converted_files=results,
                total_files=total_files
            )
            
        finally:
            # 원래 작업 디렉토리로 복원
            os.chdir(original_cwd)
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"변환 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/convert-upload")
async def convert_uploaded_file(
    file: UploadFile = File(...),
    convert_to: Optional[str] = Form(None),
    api_key_valid: bool = Depends(verify_api_key)
):
    """
    업로드된 파일을 변환하고 변환된 파일을 직접 반환합니다.
    
    - **file**: 변환할 파일 (업로드)
    - **convert_to**: 변환할 확장자 (선택사항)
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        file_content = await file.read()
        
        validate_file(file_content, file.filename or "unknown")
        
        temp_input = Path(temp_dir) / file.filename
        with open(temp_input, "wb") as buffer:
            buffer.write(file_content)
        
        original_cwd = os.getcwd()
        
        try:
            os.chdir(temp_dir)
            
            outputs = convert_any(str(temp_input), convert_to)
            
            if not outputs:
                raise HTTPException(
                    status_code=400,
                    detail="지원하지 않는 파일 형식이거나 변환에 실패했습니다."
                )
            
            converted_file_path = outputs[0]
            converted_file = Path(converted_file_path)
            
            if not converted_file.exists():
                raise HTTPException(
                    status_code=500,
                    detail="변환된 파일을 찾을 수 없습니다."
                )
            
            mime_type, _ = mimetypes.guess_type(str(converted_file))
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            return FileResponse(
                path=str(converted_file),
                filename=converted_file.name,
                media_type=mime_type,
                background=lambda: shutil.rmtree(temp_dir, ignore_errors=True)
            )
            
        finally:
            os.chdir(original_cwd)
            
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail=f"파일 업로드 및 변환 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "message": "File Converter API is running"}

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )
