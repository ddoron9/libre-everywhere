#!/bin/bash

# File Converter API - Offline Load and Run Script
# 이 스크립트는 폐쇄망 환경에서 실행하여 Docker 이미지를 로드하고 실행합니다.

set -e

IMAGE_NAME="file-converter-api"
IMAGE_TAG="latest"
EXPORT_FILE="file-converter-api.tar"
CONTAINER_NAME="file-converter-api-container"

echo "🔄 Loading and running Docker image in offline environment..."

# 1. 체크섬 검증 (파일이 있는 경우)
if [ -f "${EXPORT_FILE}.sha256" ]; then
    echo "🔐 Verifying checksum..."
    sha256sum -c ${EXPORT_FILE}.sha256
    echo "✅ Checksum verified!"
else
    echo "⚠️  No checksum file found, skipping verification"
fi

# 2. Docker 이미지 로드
if [ -f "${EXPORT_FILE}" ]; then
    echo "📦 Loading Docker image from ${EXPORT_FILE}..."
    docker load -i ${EXPORT_FILE}
    echo "✅ Image loaded successfully!"
else
    echo "❌ Error: ${EXPORT_FILE} not found!"
    exit 1
fi

# 3. 기존 컨테이너 정리 (있는 경우)
if docker ps -a --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "🧹 Removing existing container..."
    docker rm -f ${CONTAINER_NAME}
fi

# 4. 필요한 디렉토리 생성
echo "📁 Creating required directories..."
mkdir -p uploads converted_files data

# 5. Docker 컨테이너 실행
echo "🚀 Starting container: ${CONTAINER_NAME}"
docker run -d \
    --name ${CONTAINER_NAME} \
    -p 8000:8000 \
    -v $(pwd)/uploads:/app/uploads \
    -v $(pwd)/converted_files:/app/converted_files \
    -v $(pwd)/data:/app/data:ro \
    --restart unless-stopped \
    ${IMAGE_NAME}:${IMAGE_TAG}

# 6. 컨테이너 상태 확인
echo "⏳ Waiting for container to start..."
sleep 10

if docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -q "^${CONTAINER_NAME}"; then
    echo "✅ Container is running!"
    echo ""
    echo "📋 Container Information:"
    docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep ${CONTAINER_NAME}
    echo ""
    echo "🌐 API is available at: http://localhost:8000"
    echo "📚 API Documentation: http://localhost:8000/docs"
    echo ""
    echo "🔍 Useful commands:"
    echo "  docker logs ${CONTAINER_NAME}           # View logs"
    echo "  docker exec -it ${CONTAINER_NAME} bash  # Enter container"
    echo "  docker stop ${CONTAINER_NAME}           # Stop container"
    echo "  docker start ${CONTAINER_NAME}          # Start container"
else
    echo "❌ Container failed to start!"
    echo "📋 Container logs:"
    docker logs ${CONTAINER_NAME}
    exit 1
fi
