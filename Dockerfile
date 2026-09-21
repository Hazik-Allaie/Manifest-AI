# Manifest AI — Production Cloud Run Dockerfile
# Optimized multi-stage build with non-root security and health check probe

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    APP_HOME=/app

WORKDIR $APP_HOME

# Install OS build dependencies for C-extensions (python-Levenshtein, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create non-root user for Cloud Run container security
RUN useradd -m -u 1000 manifest && chown -R manifest:manifest $APP_HOME
USER manifest

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Health check configuration
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Launch production server via Uvicorn
CMD ["uvicorn", "dashboard.server:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
