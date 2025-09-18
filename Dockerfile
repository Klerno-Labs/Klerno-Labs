# ==============================================================================
# Klerno Labs — Production-Ready Multi-Stage Dockerfile (FastAPI / Uvicorn)
# ==============================================================================

ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS base

# System hardening & useful env
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONFAULTHANDLER=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  PIP_DEFAULT_TIMEOUT=100

# OS deps (base, minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
  ca-certificates curl dumb-init \
  && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1000 appuser \
  && useradd -u 1000 -g appuser -s /usr/sbin/nologin -m appuser

# ------------------------------------------------------------------------------
# Builder: install build tools & create venv with deps
# ------------------------------------------------------------------------------
FROM base AS builder
WORKDIR /app

# Build deps for any packages that need compilation (kept only in builder)
RUN apt-get update && apt-get install -y --no-install-recommends \
  gcc g++ build-essential \
  && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better layer caching
COPY requirements.txt /app/requirements.txt

# Create a dedicated venv in /opt/venv and install python deps there
RUN python -m venv /opt/venv \
  && . /opt/venv/bin/activate \
  && pip install --upgrade pip wheel setuptools \
  && pip install -r /app/requirements.txt

# ------------------------------------------------------------------------------
# Development stage (optional) — hot-reload, linters, tests
# ------------------------------------------------------------------------------
FROM builder AS development
WORKDIR /app

# Dev-only tools
RUN . /opt/venv/bin/activate \
  && pip install pytest pytest-asyncio pytest-cov black isort ruff mypy

# App source
COPY --chown=appuser:appuser . /app/

USER appuser
ENV PATH="/opt/venv/bin:${PATH}"
EXPOSE 8000
ENTRYPOINT ["dumb-init","--"]
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--reload"]

# ------------------------------------------------------------------------------
# Production stage — slim runtime image
# ------------------------------------------------------------------------------
FROM base AS production
WORKDIR /app

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# Copy application code (only what you need at runtime)
# If your project has other top-level files that the app imports, keep this COPY *.py
COPY --chown=appuser:appuser app/ /app/app/
COPY --chown=appuser:appuser *.py /app/

# Create runtime dirs with safe perms
RUN mkdir -p /app/data /app/logs /app/static \
  && chown -R appuser:appuser /app

# Security hygiene
RUN find /app -type f -name "*.py" -exec chmod 0644 {} \; \
  && find /app -type d -exec chmod 0755 {} \;

USER appuser

# App runtime env (override at deploy time as needed)
ENV APP_ENV=production \
  PORT=8000 \
  WORKERS=1 \
  LOG_LEVEL=info

# Healthcheck (use unauthenticated endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -fsS http://localhost:${PORT}/healthz || exit 1

EXPOSE 8000

ENTRYPOINT ["dumb-init","--"]
CMD ["sh","-c", "\
  echo 'Starting Klerno Labs Application...' && \
  echo 'Environment: ${APP_ENV}' && \
  echo 'Port: ${PORT}' && \
  echo 'Workers: ${WORKERS}' && \
  uvicorn app.main:app \
  --host 0.0.0.0 \
  --port ${PORT} \
  --workers ${WORKERS} \
  --log-level ${LOG_LEVEL} \
  --access-log \
  "]