# =============================================================================
# Automaton Auditor - Dockerfile
# =============================================================================
# This Dockerfile containerizes the Automaton Auditor for production deployment.
# It sets up Python, installs dependencies, and configures the environment.
# =============================================================================

# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# =============================================================================
# Install system dependencies
# =============================================================================
# - git: Required for cloning repositories
# - poppler-utils: Required for PDF processing (pdftoppm, pdftocairo)
# - tesseract-ocr: Required for OCR if needed
# =============================================================================
RUN apt-get update && apt-get install -y \
    git \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Copy dependency files
# =============================================================================
COPY requirements.txt pyproject.toml ./

# =============================================================================
# Install Python dependencies
# =============================================================================
# Use pip install with no cache for smaller image
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Copy source code
# =============================================================================
COPY src/ ./src/
COPY dashboard/ ./dashboard/
COPY tests/ ./tests/

# =============================================================================
# Copy environment example and create .env
# =============================================================================
COPY .env.example ./.env.example

# Create .env from .env.example (user must fill in actual values)
RUN cp .env.example .env

# =============================================================================
# Create output directories
# =============================================================================
RUN mkdir -p /app/audit/report_onself_generated \
             /app/audit/report_onpeer_generated \
             /app/audit/report_bypeer_received

# =============================================================================
# Environment variables
# =============================================================================
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# =============================================================================
# Expose dashboard port
# =============================================================================
EXPOSE 8000

# =============================================================================
# Health check
# =============================================================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# =============================================================================
# Default command: show help
# =============================================================================
CMD ["python", "-c", "print('Automaton Auditor Docker Container')"]
