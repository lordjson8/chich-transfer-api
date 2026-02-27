#!/bin/sh
# Production entrypoint script for the Django container.
# This runs every time the container starts (or restarts).
# It prepares the app before handing off to Gunicorn.

# Exit immediately if any command fails (-e flag).
# This prevents the container from starting in a broken state.
set -e

# Verify the database is reachable before attempting migrations.
# Django's "check --database" tests the DB connection using settings.
echo "Waiting for database..."
python manage.py check --database default

# Apply any pending database schema changes.
# "migrate" applies migrations that were created during development.
# We NEVER run "makemigrations" in production — migrations must be
# committed to Git and reviewed before deploying.
echo "Applying database migrations..."
python manage.py migrate --noinput

# Gather all static files (CSS, JS, images) from Django apps
# into a single directory (STATIC_ROOT = /app/staticfiles).
# Nginx will serve these directly, bypassing Django for performance.
# --noinput means don't prompt for confirmation.
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create the log directory so Django's file logger doesn't fail.
# This path matches LOGGING['handlers']['file']['filename'] in production.py.
echo "Creating log directory..."
mkdir -p /var/log/moneytransfer

# Start Gunicorn — the production WSGI server for Django.
# "exec" replaces this shell process with Gunicorn, so Gunicorn
# becomes PID 1 in the container and receives signals (SIGTERM, etc.)
# properly for graceful shutdown.
echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-class gthread \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
# --bind 0.0.0.0:8000    → Listen on all interfaces, port 8000 (internal to Docker network)
# --workers 3             → 3 worker processes (rule of thumb: 2*CPU + 1)
# --worker-class gthread  → Use threaded workers (good for I/O-bound Django apps)
# --threads 2             → 2 threads per worker = 6 concurrent requests total
# --timeout 120           → Kill workers that are silent for 120 seconds
# --access-logfile -      → Print access logs to stdout (Docker captures stdout)
# --error-logfile -       → Print error logs to stdout
