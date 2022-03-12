#!/bin/bash

set -xe

docker-compose pull

SHA=$(docker inspect -f '{{ index .Config.Labels "org.opencontainers.image.revision" }}' ghcr.io/meine-stadt-transparent/meine-stadt-transparent:main)
VERSION="meine-stadt-transparent@${SHA}"
echo $VERSION

sentry-cli releases new -p mst-many "$VERSION"
sentry-cli releases set-commits "$VERSION" --commit "meine-stadt-transparent/meine-stadt-transparent@${SHA}"

docker-compose up -d
echo "Deployment finished"

sentry-cli releases deploys "$VERSION" new -e staging
sentry-cli releases finalize "$VERSION"
