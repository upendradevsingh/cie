FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output
# so that logs appear immediately in Docker.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required by psycopg2 and other native packages.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (leverages Docker layer caching).
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY . .

# Create the uploads directory for local file storage.
RUN mkdir -p /app/uploads && \
    chmod 755 /app/uploads

# Expose the FastAPI default port.
EXPOSE 8000

# Health check — hits the FastAPI health endpoint every 30 seconds.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command — run the FastAPI server via uvicorn.
# Override this in docker-compose for the Celery worker.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
