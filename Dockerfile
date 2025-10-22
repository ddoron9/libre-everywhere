FROM python:3.11-slim

LABEL maintainer="dykim34@crowdworks.kr"
LABEL license="GPLv2, AGPLv3"
LABEL notice="This Docker image includes GPL-licensed software: \
AbiWord (GPLv2) - source code available at https://www.abisource.com/downloads/abiword/ \
pyhwp (AGPLv3) - source code available at https://github.com/mete0r/pyhwp"

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y locales \
 && sed -i '/ko_KR.UTF-8/s/^# //g' /etc/locale.gen \
 && locale-gen ko_KR.UTF-8

ENV LANG=ko_KR.UTF-8 \
    LC_ALL=ko_KR.UTF-8 \
    TZ=UTC

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv-cache \
    DISPLAY=:99 \
    API_KEY=your-secret-api-key-change-this \
    MAX_FILE_SIZE=104857600
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libfontconfig1 \
    libreoffice \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    libxml2 \
    libxslt1.1 \
    libjpeg62-turbo \
    zlib1g \
    abiword \
    xvfb \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml ./
COPY uv.lock* ./
COPY README.md ./
COPY src/ ./src/

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]