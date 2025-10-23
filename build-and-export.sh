#!/bin/bash

# File Converter API - Offline Deployment Script
# 이 스크립트는 인터넷이 되는 환경에서 실행하여 Docker 이미지를 빌드하고 tar로 저장합니다.

set -e

IMAGE_NAME="file-converter-api"
IMAGE_TAG="latest"
EXPORT_FILE="file-converter-api.tar"

echo "🚀 Building Docker image for offline deployment..."

# 1. Docker 이미지 빌드
echo "📦 Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG}"
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

# 2. 이미지 크기 확인
echo "📊 Image size:"
docker images ${IMAGE_NAME}:${IMAGE_TAG}

# 3. Docker 이미지를 tar 파일로 저장
echo "💾 Exporting Docker image to ${EXPORT_FILE}..."
docker save ${IMAGE_NAME}:${IMAGE_TAG} -o ${EXPORT_FILE}

# 4. tar 파일 크기 확인
echo "📁 Export file size:"
ls -lh ${EXPORT_FILE}

# 5. 체크섬 생성 (무결성 검증용)
echo "🔐 Generating checksum..."
sha256sum ${EXPORT_FILE} > ${EXPORT_FILE}.sha256

echo "✅ Build and export completed!"
echo ""
echo "📋 Files created:"
echo "  - ${EXPORT_FILE} (Docker image)"
echo "  - ${EXPORT_FILE}.sha256 (checksum)"
echo ""
echo "🚚 Transfer these files to your offline environment and run:"
echo "  ./load-and-run.sh"
echo ""
echo "📝 Or manually:"
echo "  docker load -i ${EXPORT_FILE}"
echo "  docker run -p 8000:8000 ${IMAGE_NAME}:${IMAGE_TAG}"
