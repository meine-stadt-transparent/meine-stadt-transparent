FROM node:10 AS front-end

ENV NODE_ENV=production
WORKDIR /app

COPY package.json /app/package.json
COPY package-lock.json /app/package-lock.json

RUN npm ci --dev

COPY etc /app/etc
COPY customization /app/customization
COPY mainapp/assets /app/mainapp/assets
RUN npm run build:prod && npm run build:email

FROM ubuntu:18.04

ENV PYTHONUNBUFFERED=1 NODE_ENV=production
# The default locale breaks python 3 < python 3.7. https://bugs.python.org/issue28180
ENV LANG C.UTF-8

RUN apt-get update && \
    apt-get install -y curl gnupg && \
    curl -sL https://deb.nodesource.com/setup_10.x | bash - && \
    apt-get install -y python3-pip python3-venv python3-dev \
    nodejs git libmysqlclient-dev libmagickwand-dev poppler-utils libssl-dev gettext && \
    curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python3 && \
    apt-get purge -y curl gnupg && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY pyproject.toml /app/pyproject.toml
COPY poetry.lock /app/poetry.lock
WORKDIR /app

RUN $HOME/.poetry/bin/poetry config virtualenvs.in-project true && \
    $HOME/.poetry/bin/poetry install --no-dev -E import-json
COPY . /app/

COPY --from=front-end /app/mainapp/assets /app/mainapp/assets
COPY --from=front-end /app/node_modules /app/node_modules

RUN etc/docker-init.sh

EXPOSE 8000

USER www-data

ENTRYPOINT ["/app/.venv/bin/python"]
CMD ["/app/.venv/bin/gunicorn", "meine_stadt_transparent.wsgi:application", "-w 2", "-b :8000", "--capture-output"]
