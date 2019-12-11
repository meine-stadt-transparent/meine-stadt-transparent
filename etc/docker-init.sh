#!/usr/bin/env bash
# Called by docker after add the project to /app

set -e

# Generate all static files and clean up all node stuff
cp etc/template.env .env
mkdir /app/log
/app/.venv/bin/python manage.py compilemessages
/app/.venv/bin/python manage.py collectstatic --noinput
rm .env
npm install osmtogeojson  # We call that tool from python

chown -R www-data:www-data /app
