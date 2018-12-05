#!/bin/bash

set -xe

git fetch
git reset --hard origin/master
poetry install --no-dev
poetry run python ./manage.py migrate
poetry run python ./manage.py compilemessages
npm ci
npm run build:prod
poetry run python ./manage.py collectstatic --noinput
ps aux | grep gunicorn | grep meine | awk '{ print $2 }' | xargs kill -HUP
echo "Deployment finished"
