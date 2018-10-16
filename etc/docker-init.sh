#!/usr/bin/env bash
# Called by docker after add the project to /app

set -e

# Setup the python part
pip3 install --upgrade poetry
poetry config settings.virtualenvs.in-project true
poetry install --no-dev
ln -s /usr/lib/python3/dist-packages/gi /app/.venv/lib/python*/site-packages/

# Setup the npm part
npm install && npm run build:prod && npm run build:email

# Allow overriding the default env
mkdir /config && cp etc/env-docker-compose /config/.env && (cp .env-docker-compose /config/.env || true) && rm -f .env

poetry run python manage.py collectstatic --noinput
rm -rf node_modules # We need them until after collectstatic for pdfjs-dist

chown -R www-data:www-data /config
chown -R www-data:www-data /app
