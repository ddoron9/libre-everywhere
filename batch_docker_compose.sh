#!/bin/bash

# Docker Compose를 사용한 대량 파일 변환 스크립트
# Usage: ./batch_docker_compose.sh /path/to/files [replicas]

set -e

INPUT_DIR="${1:-$(pwd)/test/data}"
REPLICAS="${2:-4}"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🐳 Docker Compose 대량 변환 시작${NC}"
echo -e "${BLUE}📁 입력 디렉토리: ${INPUT_DIR}${NC}"
echo -e "${BLUE}🔄 병렬 인스턴스: ${REPLICAS}개${NC}"

# 환경 변수 설정
export INPUT_DIR="$INPUT_DIR"
export REPLICAS="$REPLICAS"
export UID=$(id -u)
export GID=$(id -g)

# Docker 이미지 빌드
echo -e "${YELLOW}🔨 Docker 이미지 빌드 중...${NC}"
docker-compose build

# 파일 개수 확인
TOTAL_FILES=$(find "$INPUT_DIR" -type f \( -name "*.doc" -o -name "*.hwp" -o -name "*.xls" -o -name "*.ppt" -o -name "*.mht" \) 2>/dev/null | wc -l)

if [ "$TOTAL_FILES" -eq 0 ]; then
    echo -e "${RED}❌ 변환할 파일이 없습니다.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 총 ${TOTAL_FILES}개 파일 발견${NC}"

# 변환 실행
echo -e "${YELLOW}🚀 변환 작업 시작...${NC}"
docker-compose up --scale file-converter-batch=$REPLICAS

echo -e "${GREEN}🎉 변환 작업 완료!${NC}"

# 정리
echo -e "${BLUE}🧹 컨테이너 정리 중...${NC}"
docker-compose down

echo -e "${BLUE}✨ 모든 작업 완료!${NC}"
