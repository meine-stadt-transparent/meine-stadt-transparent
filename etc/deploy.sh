#!/bin/bash

set -xe

git fetch
git reset --hard origin/master

VERSION="meine-stadt-transparent@$(git rev-parse HEAD)"
export SENTRY_ORG=konstin

sentry-cli releases new -p meine-stadt-transparent-de "$VERSION"
sentry-cli releases set-commits "$VERSION" --auto

poetry install --no-dev
poetry run python ./manage.py migrate
poetry run python ./manage.py compilemessages
npm ci
npm run build:prod
poetry run python ./manage.py collectstatic --noinput
ps aux | grep gunicorn | grep meine | awk '{ print $2 }' | xargs kill -HUP
echo "Deployment finished"

sentry-cli releases deploys "$VERSION" new -e staging
sentry-cli releases finalize "$VERSION"
