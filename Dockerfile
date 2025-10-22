FROM python:3.8-slim
WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice libreoffice-impress libreoffice-writer libreoffice-calc \
    default-jre \
    # WeasyPrint runtime libs
    libxml2 libxslt1.1 libcairo2 libpangocairo-1.0-0 pango1.0-tools libpango-1.0-0 libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 libjpeg62-turbo libpng16-16 libharfbuzz0b libfribidi0 \
    # misc utilities
    libffi-dev shared-mime-info curl unzip ca-certificates \
    # fonts
    fonts-dejavu-core fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml /app/
COPY convert.py /app/convert.py
COPY MhtmlExtractor.py /app/MhtmlExtractor.py
COPY config.py /app/config.py

# Install dependencies using uv with pyproject.toml
RUN uv pip install --system --no-cache -e ".[hwp,fallbacks]"

VOLUME ["/data"]
ENTRYPOINT ["python", "/app/convert.py"]
CMD ["/data"]