# Build stage
FROM quay.io/cwt/python:3.14-optimized-alpine as builder

# Install build dependencies
RUN apk update \
 && apk upgrade \
 && apk add --no-cache \
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
    tcl-dev \
    cmake \
    make \
    sqlite-dev \
    icu-dev \
    git \
    bash \
    libwebp-dev \
    libpng-dev

# Clone fts5-icu-tokenizer repository
RUN git clone https://github.com/cwt/fts5-icu-tokenizer.git /tmp/fts5-icu-tokenizer

# Build fts5-icu-tokenizer
RUN cd /tmp/fts5-icu-tokenizer && \
    chmod +x scripts/build_all.sh && \
    bash scripts/build_all.sh

# Create app directory and copy built tokenizer libraries
RUN mkdir -p /app/tokenizers && \
    find /tmp/fts5-icu-tokenizer -name "*.so" -exec cp {} /app/tokenizers/ \; && \
    find /tmp/fts5-icu-tokenizer -name "*.dylib" -exec cp {} /app/tokenizers/ \; && \
    find /tmp/fts5-icu-tokenizer -name "*.dll" -exec cp {} /app/tokenizers/ \; && \
    chmod +r /app/tokenizers/*

# Runtime stage
FROM quay.io/cwt/python:3.14-optimized-alpine

# Set labels for image metadata
LABEL maintainer="Neo Bloggy Team"
LABEL description="Neo Bloggy - A modern blogging platform using NeoSQLite"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV NEO_BLOGGY_CONFIG_PATH=/data/config.toml
ENV FTS5_ICU_TOKENIZER_PATH=/app/tokenizers

# Install runtime dependencies (only what's needed to run the application)
RUN apk update \
 && apk upgrade --no-cache \
 && apk add --no-cache \
    libffi \
    openssl \
    jpeg \
    zlib \
    freetype \
    lcms2 \
    openjpeg \
    tiff \
    tk \
    tcl \
    sqlite-libs \
    icu-libs \
    icu-data-full \
    bash \
    libwebp \
    libpng

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

# Copy built tokenizer libraries from the builder stage
COPY --from=builder /app/tokenizers /app/tokenizers

VOLUME /data

# Create a non-root user for security
RUN adduser -D -s /bin/sh -u 1000 appuser
RUN chown -R appuser:appuser /app /data
RUN chmod -R 755 /app/tokenizers
USER appuser

# Expose port for the application
EXPOSE 8000

# Default command with Gunicorn production WSGI server using config file
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
