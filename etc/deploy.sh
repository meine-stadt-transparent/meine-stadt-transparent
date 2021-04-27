#!/bin/bash

set -xe

git fetch
git reset --hard origin/main

docker-compose pull

VERSION="meine-stadt-transparent@$(git rev-parse HEAD)"
export SENTRY_ORG=konstin

sentry-cli releases new -p meine-stadt-transparent-de "$VERSION"
sentry-cli releases set-commits "$VERSION" --auto

docker-compose up -d
echo "Deployment finished"

sentry-cli releases deploys "$VERSION" new -e staging
sentry-cli releases finalize "$VERSION"
