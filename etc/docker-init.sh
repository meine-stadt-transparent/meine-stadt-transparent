#!/usr/bin/env bash
# Called by docker after add the project to /app

set -e

# Setup the python part
pip3 install --upgrade poetry
poetry config settings.virtualenvs.in-project true
poetry install --no-dev
ln -s /usr/lib/python3/dist-packages/gi /app/.venv/lib/python*/site-packages/

# Generate all static files and clean up all node stuff
apt-get install nodejs -y
npm install
npm run build:prod
npm run build:email
cp etc/env-template .env
poetry run python manage.py collectstatic --noinput
rm .env
apt-get remove nodejs -y
apt-get clean
rm -rf node_modules # We need them until after collectstatic for pdfjs-dist

chown -R www-data:www-data /app
