#!/usr/bin/env bash
# Build script for Render deployment.
# Render runs this before starting the web server.

set -e  # exit immediately if any command fails

echo "--- Installing Python dependencies ---"
pip install -r requirements.txt

echo "--- Running database migrations ---"
python manage.py migrate --no-input

echo "--- Collecting static files ---"
python manage.py collectstatic --no-input

echo "--- Seeding emission factors and admin user ---"
python seed_db.py

echo "--- Build complete ---"
