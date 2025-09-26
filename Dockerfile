FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# System build deps (removed later in final stage if heavy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

FROM base AS dev-deps
COPY dev-requirements.txt .
RUN pip install -r dev-requirements.txt || true

FROM base AS runtime
LABEL org.opencontainers.image.source="https://github.com/Klerno-Labs/Klerno-Labs" \
    org.opencontainers.image.title="Klerno Labs" \
    org.opencontainers.image.description="Klerno Labs Enterprise Platform" \
    org.opencontainers.image.licenses="Apache-2.0"

# Copy application code last for better layer caching
COPY . .

# Create least-privileged user
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use uvicorn with app.main:app (enterprise_main_v2 kept for legacy but not default)
ENV HOST=0.0.0.0 PORT=8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
