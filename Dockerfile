# FitIntel Pro — Dockerfile (Linux: Ubuntu/Debian, x86_64)
# Быстрая сборка: тяжёлые зависимости (dlib/face-recognition) — в requirements-base.txt
# (слой кэшируется, меняется редко). Лёгкие — в requirements.txt.

FROM python:3.12-slim AS base
WORKDIR /app

# System deps (build tools + ускорение dlib + pyscard)
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

# ТЯЖЁЛЫЕ зависимости — отдельный слой (кэш ~вечный)
COPY requirements-base.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements-base.txt

# ЛЁГКИЕ зависимости — быстрый слой (изменения = 1-2 мин, dlib не трогается)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini .
COPY celery_app.py .
COPY scripts/create_admin.py scripts/bootstrap_db.py ./scripts/

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
# каталог опционального хранения фото лиц — сразу с правами appuser
# (иначе named volume создаётся под root и API не сможет писать)
RUN mkdir -p /app/data/face_photos && chown -R appuser:appuser /app/data
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]