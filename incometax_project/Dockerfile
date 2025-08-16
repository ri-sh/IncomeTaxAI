# Use Python 3.10 slim image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    pkg-config \
    curl \
    wget \
    ghostscript \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create directories for static files and media
RUN mkdir -p /app/static /app/media

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Create a non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# Create and set permissions for NLTK data
RUN mkdir -p /app/nltk_data && chown -R app:app /app/nltk_data
ENV NLTK_DATA=/app/nltk_data

USER app

# Expose port
EXPOSE 8000

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "incometax_project.wsgi:application"]