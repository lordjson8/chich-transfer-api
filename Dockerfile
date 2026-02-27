# --------------------------------------------------------------------------
# Dockerfile — Builds the Django application image
# --------------------------------------------------------------------------
# This file tells Docker how to create an image containing our Django app
# and all its dependencies. Think of it as a recipe for a portable box
# that can run anywhere Docker is installed.
# --------------------------------------------------------------------------

# Start from the official Python 3.12 "slim" image.
# "slim" is a minimal Debian image with Python pre-installed (~150MB vs ~900MB full).
# Using an official image ensures security patches are maintained upstream.
FROM python:3.12-slim

# Set environment variables that improve Python's behavior inside Docker:
# PYTHONDONTWRITEBYTECODE=1 → Don't create .pyc bytecode files (saves disk space)
# PYTHONUNBUFFERED=1        → Print output immediately (don't buffer), so logs appear in real-time
# PIP_NO_CACHE_DIR=1        → Don't cache pip downloads (saves disk space in the image)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Set the working directory inside the container to /app.
# All subsequent commands (RUN, COPY, CMD) will execute relative to this path.
WORKDIR /app

# Install OS-level libraries that Python packages need to compile.
# These are C libraries that pip packages like mysqlclient and psycopg2 depend on.
# --no-install-recommends → Only install strictly required packages (smaller image)
# rm -rf /var/lib/apt/lists/* → Delete apt cache to reduce image size
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    libpq-dev \
    pkg-config && \
    rm -rf /var/lib/apt/lists/*
# build-essential            → C compiler and make (needed to compile Python C extensions)
# default-libmysqlclient-dev → MySQL client headers (needed by mysqlclient pip package)
# libpq-dev                  → PostgreSQL client headers (needed by psycopg2 pip package)
# pkg-config                 → Helper tool that finds library paths during compilation

# Copy ONLY the requirements folder first.
# Docker caches each step (layer). By copying requirements separately, Docker
# can skip re-installing packages if only your code changed (not dependencies).
# This dramatically speeds up rebuilds during development.
COPY requirements /app/requirements

# ARG defines a build-time variable. It can be overridden in docker-compose.yml.
# Default: development.txt (for local dev). Production compose passes production.txt.
ARG REQUIREMENTS_FILE=requirements/development.txt

# Install Python packages from the requirements file.
# --no-cache-dir → Don't store pip's download cache (smaller image)
RUN pip install --no-cache-dir -r ${REQUIREMENTS_FILE}


# Create the logging directory and file
RUN mkdir -p /var/log/moneytransfer && \
    touch /var/log/moneytransfer/app.log && \
    chmod -R 777 /var/log/moneytransfer

# NOW copy the entire project code into the image.
# This step is intentionally AFTER pip install — if you only change code (not deps),
# Docker reuses the cached pip install layer and only re-runs this COPY.
COPY . /app/

# Document that this container listens on port 8000.
# EXPOSE doesn't actually publish the port — it's metadata for developers
# and tools. The actual port mapping is done in docker-compose.yml.
EXPOSE 8000

# Default command — used only if no command/entrypoint is specified.
# In production, docker-compose overrides this with entrypoint.prod.sh (Gunicorn).
# In development, this runs Django's built-in dev server.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
