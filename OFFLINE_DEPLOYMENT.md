# 폐쇄망 환경 배포 가이드

이 가이드는 인터넷이 차단된 폐쇄망 환경에서 File Converter API를 배포하는 방법을 설명합니다.

## 🔄 배포 프로세스 개요

1. **인터넷 환경**: Docker 이미지 빌드 및 tar 파일로 저장
2. **파일 전송**: tar 파일을 폐쇄망으로 이동
3. **폐쇄망 환경**: Docker 이미지 로드 및 컨테이너 실행

## 📦 1단계: 이미지 빌드 및 저장 (인터넷 환경)

### 자동 빌드 스크립트 사용
```bash
./build-and-export.sh
```

### 수동 빌드
```bash
# 1. Docker 이미지 빌드
docker build -t file-converter-api:latest .

# 2. 이미지를 tar 파일로 저장
docker save file-converter-api:latest -o file-converter-api.tar

# 3. 체크섬 생성 (선택사항)
sha256sum file-converter-api.tar > file-converter-api.tar.sha256
```

## 🚚 2단계: 파일 전송

다음 파일들을 폐쇄망 환경으로 복사:
- `file-converter-api.tar` (Docker 이미지)
- `file-converter-api.tar.sha256` (체크섬, 선택사항)
- `load-and-run.sh` (실행 스크립트)
- `docker-compose.offline.yml` (Docker Compose 파일, 선택사항)

## 🔄 3단계: 이미지 로드 및 실행 (폐쇄망 환경)

### 자동 로드 및 실행
```bash
./load-and-run.sh
```

### 수동 로드 및 실행
```bash
# 1. 체크섬 검증 (선택사항)
sha256sum -c file-converter-api.tar.sha256

# 2. Docker 이미지 로드
docker load -i file-converter-api.tar

# 3. 필요한 디렉토리 생성
mkdir -p uploads converted_files temp_test_files data

# 4. 컨테이너 실행
docker run -d \
    --name file-converter-api-container \
    -p 8000:8000 \
    -v $(pwd)/uploads:/app/uploads \
    -v $(pwd)/converted_files:/app/converted_files \
    -v $(pwd)/temp_test_files:/app/temp_test_files \
    -v $(pwd)/data:/app/data:ro \
    --restart unless-stopped \
    file-converter-api:latest
```


## 🔍 4단계: 동작 확인

### API 상태 확인
```bash
# 컨테이너 상태 확인
docker ps

# API 헬스 체크 (컨테이너 내부에서)
docker exec file-converter-api-container python3 -c "
import urllib.request
try:
    response = urllib.request.urlopen('http://localhost:8000/health')
    print('API Status:', response.read().decode())
except Exception as e:
    print('API Error:', e)
"
```

### 로그 확인
```bash
# 컨테이너 로그 확인
docker logs file-converter-api-container

# 실시간 로그 모니터링
docker logs -f file-converter-api-container
```

## 🛠️ 오프라인 환경 특화 설정

### 1. 완전 오프라인 모드
네트워크를 완전히 차단하려면 Docker 실행 시 다음 옵션 추가:
```bash
docker run --network none ...
```

### 2. 헬스 체크 수정
인터넷 접근이 불가능한 환경에서는 Python의 내장 라이브러리만 사용:
```dockerfile
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
```

## 📋 트러블슈팅

### 이미지 로드 실패
```bash
# 이미지 파일 무결성 확인
file file-converter-api.tar

# Docker 데몬 상태 확인
systemctl status docker
```

### 컨테이너 실행 실패
```bash
# 포트 충돌 확인
netstat -tulpn | grep 8000

# 볼륨 권한 확인
ls -la uploads/ converted_files/ temp_test_files/
```

### 의존성 문제
```bash
# 컨테이너 내부 접근
docker exec -it file-converter-api-container bash

# Python 패키지 확인
docker exec file-converter-api-container uv pip list
```

## 🔧 유지보수

### 컨테이너 관리
```bash
# 컨테이너 중지
docker stop file-converter-api-container

# 컨테이너 시작
docker start file-converter-api-container

# 컨테이너 재시작
docker restart file-converter-api-container

# 컨테이너 삭제
docker rm -f file-converter-api-container
```

### 이미지 관리
```bash
# 이미지 목록 확인
docker images

# 사용하지 않는 이미지 정리
docker image prune

# 특정 이미지 삭제
docker rmi file-converter-api:latest
```

## 📊 성능 모니터링

### 리소스 사용량 확인
```bash
# 컨테이너 리소스 사용량
docker stats file-converter-api-container

# 시스템 리소스 확인
docker system df
```

### 로그 관리
```bash
# 로그 크기 제한 설정
docker run -d \
    --log-opt max-size=10m \
    --log-opt max-file=3 \
    --name file-converter-api-container \
    file-converter-api:latest
```
