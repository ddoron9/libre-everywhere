# Use Python 3.11 slim image
FROM python:3.11-slim

# License and maintainer information
LABEL maintainer="dykim34@crowdworks.kr"
LABEL license="GPLv2, GPLv3"
LABEL notice="This Docker image includes GPL-licensed software: \
AbiWord (GPLv2) - source code available at https://www.abisource.com/downloads/abiword/ \
pyhwp (GPLv3) - source code available at https://github.com/mete0r/pyhwp"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv-cache \
    DISPLAY=:99

# Install system dependencies for WeasyPrint, LibreOffice, and AbiWord
RUN apt-get update && apt-get install -y \
    # WeasyPrint dependencies
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libfontconfig1 \
    # LibreOffice
    libreoffice \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    # AbiWord (fallback for document conversion)
    abiword \
    # Virtual display for headless operation
    xvfb \
    # Additional utilities
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create app directory
WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY uv.lock* ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Create directories for file processing
RUN mkdir -p /app/uploads /app/converted_files

# Expose port
EXPOSE 8000

# Health check (using python instead of curl for offline compatibility)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]