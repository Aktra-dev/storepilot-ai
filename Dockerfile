# ============================================
# StorePilot AI — Production Dockerfile
# ============================================
# Multi-stage build for minimal image size

# ---- Build Stage ----
FROM python:3.10-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Runtime Stage ----
FROM python:3.10-slim

WORKDIR /app

# Install runtime deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create non-root user
RUN addgroup --system --gid 1001 storepilot && \
    adduser --system --uid 1001 storepilot && \
    chown -R storepilot:storepilot /app

USER storepilot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import http.client; c=http.client.HTTPConnection('localhost:8000'); c.request('GET','/api/health'); r=c.getresponse(); exit(0 if r.status==200 else 1)"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
