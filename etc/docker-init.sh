#!/usr/bin/env bash
# Called by docker after add the project to /app

set -e

# Generate all static files and clean up all node stuff
npm ci --dev
npm run build:prod
npm run build:email
cp etc/env-template .env
poetry run python manage.py compilemessages
poetry run python manage.py collectstatic --noinput
rm .env
rm -rf node_modules # We need them until after collectstatic for pdfjs-dist
npm install osmtogeojson  # We call that tool from python

chown -R www-data:www-data /app
