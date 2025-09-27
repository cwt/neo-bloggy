# Use Alpine 3.22.1 as base image for minimal size and multi-arch support
FROM alpine:3.22.1

# Set labels for image metadata
LABEL maintainer="Neo Bloggy Team"
LABEL description="Neo Bloggy - A modern blogging platform using NeoSQLite"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV NEO_BLOGGY_CONFIG_PATH=/data/config.toml

# Install Python, pip, and build dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    jpeg-dev \
    zlib-dev \
    freetype-dev \
    lcms2-dev \
    openjpeg-dev \
    tiff-dev \
    tk-dev \
    tcl-dev

# Create app directory
WORKDIR /app

# Create a virtual environment and activate it
RUN python3 -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (excluding database and config files)
COPY . .

VOLUME /data

# Create a non-root user for security
RUN adduser -D -s /bin/sh -u 1000 appuser
RUN chown -R appuser:appuser /app /data
USER appuser

# Expose port for the application
EXPOSE 8000

# Default command with Gunicorn production WSGI server using config file
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
