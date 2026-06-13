FROM python:3.11-slim

LABEL maintainer="Sriram Sangeeth Mantha <sriram.sangeet@gmail.com>"
LABEL description="Buddy AI - Comprehensive AI Agent Framework"
LABEL version="2.0.0"

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./

RUN pip install --upgrade pip && \
    pip install -e ".[irag]"

COPY buddy/ ./buddy/

RUN python -c "import buddy; print(f'buddy-ai {buddy.__version__} installed successfully')"

EXPOSE 7777 8501

CMD ["python", "-m", "buddy.app.fastapi.app"]
