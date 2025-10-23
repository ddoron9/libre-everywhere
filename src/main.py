import mimetypes
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import uvicorn
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.convert import convert_any, convert_path
from src.logging_config import get_logger, setup_logging
from src.security import verify_api_key, validate_uploaded_file

setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="File Converter API",
    description="File and folder conversion API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_and_timing_middleware(request: Request, call_next):
    start_time = request.state.start_time = __import__("time").time()

    response = await call_next(request)

    process_time = __import__("time").time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s"
    )

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


@app.get("/supported-formats")
async def get_supported_formats(api_key_valid: bool = Depends(verify_api_key)):
    from src.convert import CONVERSION_MAPPINGS 

    logger.info("Supported formats requested")
    return {
        "supported_formats": CONVERSION_MAPPINGS,
        "description": "Key: input format, Value: list of output formats",
    }


@app.post("/convert", response_model=ConvertResponse)
async def convert_files_endpoint(
    request: ConvertRequest, api_key_valid: bool = Depends(verify_api_key)
):
    logger.info(
        f"Convert request: input={request.input_path}, output={request.output_path}, convert_to={request.convert_to}"
    )

    try:
        input_path = Path(request.input_path).resolve()

        if not input_path.exists():
            logger.error(f"Input path not found: {input_path}")
            raise HTTPException(
                status_code=404, detail=f"Input path not found: {request.input_path}"
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
                logger.warning("No files to convert")
                return ConvertResponse(
                    success=True,
                    message="No files to convert.",
                    converted_files={},
                    total_files=0,
                )

            logger.info(f"Conversion completed: {total_files} files converted")

            return ConvertResponse(
                success=True,
                message=f"Successfully converted {total_files} files.",
                converted_files=results,
                total_files=total_files,
            )

        finally:
            os.chdir(original_cwd)

    except Exception as e:
        logger.error(f"Conversion error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")


@app.post("/convert-upload")
async def convert_upload_endpoint(
    file: UploadFile = File(...),
    convert_to: Optional[str] = Form(None),
    api_key_valid: bool = Depends(verify_api_key),
):
    logger.info(
        f"File upload request: filename={file.filename}, convert_to={convert_to}"
    )

    temp_dir = tempfile.mkdtemp()

    try:
        file_content = await file.read()

        validate_uploaded_file(file_content, file.filename or "unknown")

        temp_input = Path(temp_dir) / file.filename
        with open(temp_input, "wb") as buffer:
            buffer.write(file_content)

        original_cwd = os.getcwd()

        try:
            os.chdir(temp_dir)

            outputs = convert_any(str(temp_input), convert_to)

            if not outputs:
                logger.error(f"Conversion failed for file: {file.filename}")
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file format or conversion failed.",
                )

            converted_file_path = outputs[0]
            converted_file = Path(converted_file_path)

            if not converted_file.exists():
                logger.error(f"Converted file not found: {converted_file_path}")
                raise HTTPException(status_code=500, detail="Converted file not found.")

            mime_type, _ = mimetypes.guess_type(str(converted_file))
            if not mime_type:
                mime_type = "application/octet-stream"

            logger.info(
                f"File conversion successful: {file.filename} -> {converted_file.name}"
            )

            return FileResponse(
                path=str(converted_file),
                filename=converted_file.name,
                media_type=mime_type,
                background=lambda: shutil.rmtree(temp_dir, ignore_errors=True),
            )

        finally:
            os.chdir(original_cwd)

    except Exception as e:
        logger.error(f"File upload/conversion error: {str(e)}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500, detail=f"File upload/conversion error: {str(e)}"
        )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "File Converter API is running"}


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
