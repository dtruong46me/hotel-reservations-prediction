# =============================================================================
# Hotel Reservations Prediction — Production Dockerfile
# Multi-stage build: builder installs deps, runtime runs the app
# =============================================================================

# ---- Stage 1: Builder ----
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system dependencies needed for LightGBM + wheel builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---- Stage 2: Runtime ----
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Copy only runtime system libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source (hotel_prediction package + app)
COPY src/      ./src/
COPY config/   ./config/
COPY artifacts/ ./artifacts/

# Expose the Flask port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Run via gunicorn for production
CMD ["python", "-m", "gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--timeout", "120", \
     "app.main:create_app()"]
