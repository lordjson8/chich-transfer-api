#!/bin/sh

set -e

# Apply database migrations
python manage.py makemigrations
python manage.py migrate

# Collect static files (optional in dev, more for prod)
# python manage.py collectstatic --noinput

# Start Django dev server
python manage.py runserver 0.0.0.0:8000
