# File Converter API

파일/폴더를 다양한 형식으로 변환하는 FastAPI 서버입니다.

## 지원하는 변환 형식

- `.doc` → `pdf`
- `.xls`, `.xlsm` → `xlsx`
- `.ppt` → `pptx`
- `.hwp` → `pdf`
- `.mht` → `html`

## 설치 및 실행

### 방법 1: UV 사용 (권장)

#### 1. UV 설치
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 2. 의존성 설치 및 실행
```bash
# 의존성 설치
uv sync

# 서버 실행
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 방법 2: Docker 사용

```bash
# 이미지 빌드
docker build -t file-converter-api .

# 컨테이너 실행
docker run -d -p 8000:8000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/converted_files:/app/converted_files \
  -v $(pwd)/data:/app/data \
  --name file-converter-api \
  file-converter-api
```

서버가 실행되면 `http://localhost:8000`에서 접근할 수 있습니다.

## API 엔드포인트

### 1. 기본 정보
- `GET /` - API 상태 확인
- `GET /health` - 헬스 체크
- `GET /supported-formats` - 지원하는 파일 형식 목록

### 2. 파일 변환
- `POST /convert` - 로컬 파일/폴더 변환
- `POST /convert-upload` - 업로드된 파일 변환

## 사용 예시

### 로컬 파일 변환
```bash
curl -X POST "http://localhost:8000/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": "/path/to/file.doc",
    "output_path": "/path/to/output"
  }'
```

### 파일 업로드 및 변환
```bash
curl -X POST "http://localhost:8000/convert-upload" \
  -F "file=@document.doc" \
  -F "output_path=/path/to/output"
```

### 폴더 변환
```bash
curl -X POST "http://localhost:8000/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": "/path/to/folder"
  }'
```

## API 문서

서버 실행 후 다음 URL에서 자동 생성된 API 문서를 확인할 수 있습니다:
- Swagger UI: `http://localhost:8000/docs`

## UV 프로젝트 관리

```bash
# 새로운 의존성 추가
uv add package-name

# 개발 의존성 추가
uv add --dev package-name

# 의존성 업데이트
uv sync --upgrade

# 가상환경 활성화
source .venv/bin/activate

# 스크립트 실행
uv run python main.py
```

## 🔒 폐쇄망 환경 배포

### 빌드 및 저장 (인터넷 환경)
```bash
# 자동 빌드 및 저장
./build-and-export.sh

# 수동 빌드
docker build -t file-converter-api:latest .
docker save file-converter-api:latest -o file-converter-api.tar
```

### 로드 및 실행 (폐쇄망 환경)
```bash
# 자동 로드 및 실행
./load-and-run.sh

# 수동 실행
docker load -i file-converter-api.tar
docker run -d -p 8000:8000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/converted_files:/app/converted_files \
  -v $(pwd)/data:/app/data:ro \
  --name file-converter-api \
  file-converter-api:latest
```

### 주요 특징
- ✅ **완전 오프라인**: 컨테이너 실행 시 인터넷 불필요
- ✅ **무결성 검증**: SHA256 체크섬으로 파일 검증
- ✅ **자동화 스크립트**: 빌드/배포 과정 자동화
- ✅ **헬스 체크**: Python 내장 라이브러리로 상태 확인

자세한 내용은 [OFFLINE_DEPLOYMENT.md](OFFLINE_DEPLOYMENT.md)를 참조하세요.