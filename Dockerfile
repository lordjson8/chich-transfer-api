# Official Python image
FROM python:3.12-slim

# Environment variables to make Python & Django behave well in Docker
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Working directory
WORKDIR /app

# Install system-level dependencies (e.g., Postgres client, build tools)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    libpq-dev \
    pkg-config && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker layer cache
COPY requirements /app/requirements


ARG REQUIREMENTS_FILE=requirements/development.txt

RUN pip install --no-cache-dir -r ${REQUIREMENTS_FILE}

# Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project code
COPY . /app/

# Expose the port Django/Gunicorn will run on (for documentation)
EXPOSE 8000

# Default command (we will override with docker-compose entrypoint)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
