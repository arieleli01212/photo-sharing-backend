# FastAPI Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for image processing
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory with proper permissions
RUN mkdir -p uploads && chmod 755 uploads

# Set environment variables with defaults
ENV SECRET_KEY=${SECRET_KEY:-default_secret_key}
ENV GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
ENV ALGORITHM=${ALGORITHM:-HS256}
ENV ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES:-30}
ENV SERVER_HOST=${SERVER_HOST:-0.0.0.0}
ENV SERVER_PORT=${SERVER_PORT:-8000}
ENV UPLOAD_DIR=${UPLOAD_DIR:-uploads}
ENV MAX_FILE_SIZE=${MAX_FILE_SIZE:-5242880}

# Expose the port that will be used
EXPOSE ${SERVER_PORT:-8000}

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:${SERVER_PORT:-8000}/guest')" || exit 1

# Run the FastAPI application using config values
CMD uvicorn main:app --host ${SERVER_HOST:-0.0.0.0} --port ${SERVER_PORT:-8000}