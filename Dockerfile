FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy package files
COPY pyproject.toml setup.py ./
COPY src/ ./src/

# Install the package
RUN pip install --no-cache-dir -e .

# Create directories for data and logs
RUN mkdir -p /app/data /app/logs /app/models

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DAGLAB_HOME=/app

# Default command
CMD ["daglab", "--help"]