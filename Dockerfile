# FitIntel Pro — Dockerfile (Linux: Ubuntu/Debian, x86_64)
# Один requirements.txt для всех платформ: pywin32 помечен маркером win32-only
FROM python:3.12-slim

WORKDIR /app

# System deps:
#   gcc/g++/cmake/make — сборка dlib (face-recognition)
#   libpq-dev          — psycopg (PostgreSQL)
#   libpcsclite-dev    — pyscard (считыватели RFID)
#   libopenblas/liblapack — ускорение dlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    cmake \
    make \
    libpq-dev \
    libpcsclite-dev \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps (единый файл: pywin32 ставится только на Windows — маркер в requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# App code
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini .
COPY celery_app.py .
COPY scripts/create_admin.py ./scripts/create_admin.py

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check — реальный endpoint (не корень!)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

EXPOSE 8000

# 2 воркера (uvicorn под root запрещён — appuser уже задан)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]