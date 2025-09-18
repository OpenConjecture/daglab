# Multi-stage Dockerfile for DagLab
# Stage 1: Build stage
FROM python:3.13-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy only requirements first for better caching
COPY pyproject.toml setup.py ./
COPY src/daglab/__init__.py src/daglab/

# Install dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /wheels .

# Copy the rest of the source code
COPY . .

# Build the wheel
RUN python -m build --wheel --outdir /wheels

# Stage 2: Runtime stage
FROM python:3.13-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 daglab

# Set working directory
WORKDIR /app

# Copy wheels from builder
COPY --from=builder /wheels /wheels

# Install DagLab and dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --find-links /wheels daglab[all] && \
    rm -rf /wheels

# Copy configuration files
COPY config /app/config

# Create necessary directories
RUN mkdir -p /app/data /app/logs && \
    chown -R daglab:daglab /app

# Switch to non-root user
USER daglab

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    DAGLAB_CONFIG_PATH=/app/config/daglab.yaml \
    DAGLAB_DATA_PATH=/app/data \
    DAGLAB_LOG_PATH=/app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports
EXPOSE 8000

# Default command
CMD ["python", "-m", "daglab.server"]