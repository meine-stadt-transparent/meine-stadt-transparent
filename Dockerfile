# Stage 1: Build the frontend assets
FROM node:14 AS front-end

ENV NODE_ENV=production
WORKDIR /app

COPY package.json /app/package.json
COPY package-lock.json /app/package-lock.json

RUN npm ci --also=dev

COPY etc /app/etc
COPY customization /app/customization
COPY mainapp/assets /app/mainapp/assets
RUN npm run build:prod && npm run build:email

# Stage 2: Build the .venv folder
FROM python:3.8-slim-buster AS venv-build

RUN apt-get update && \
    apt-get install -y curl gnupg git default-libmysqlclient-dev libmagickwand-dev poppler-utils libssl-dev gettext && \
    curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python - --version 1.1.8

COPY pyproject.toml /app/pyproject.toml
COPY poetry.lock /app/poetry.lock
WORKDIR /app

# Poetry needs the __init__.py files
RUN mkdir cms importer mainapp meine_stadt_transparent && \
    touch Readme.md cms/__init__.py importer/__init__.py mainapp/__init__.py meine_stadt_transparent/__init__.py && \
    $HOME/.local/bin/poetry config virtualenvs.in-project true && \
    $HOME/.local/bin/poetry install --no-dev -E import-json

# Stage 3: The actual container
FROM python:3.8-slim-buster

ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y git default-libmysqlclient-dev libmagickwand-dev poppler-utils libssl-dev gettext && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    mkdir /static && \
    chown www-data:www-data -R /static

USER www-data

COPY --chown=www-data:www-data --from=venv-build /app/.venv /app/.venv
COPY --chown=www-data:www-data --from=front-end /app/mainapp/assets /app/mainapp/assets
COPY --chown=www-data:www-data --from=front-end /app/node_modules/pdfjs-dist /app/node_modules/pdfjs-dist
COPY --chown=www-data:www-data . /app/

WORKDIR /app

# Generate all static files and clean up all node stuff
RUN cp etc/template.env .env && \
    mkdir -p /app/log && \
    /app/.venv/bin/python manage.py compilemessages -l de -l en && \
    /app/.venv/bin/python manage.py collectstatic --noinput && \
    rm .env

# We inject DOCKER_GIT_SHA in github actions
ARG DOCKER_GIT_SHA
ENV DOCKER_GIT_SHA $DOCKER_GIT_SHA

EXPOSE 8000

ENTRYPOINT ["/app/.venv/bin/python"]
CMD ["/app/.venv/bin/gunicorn", "--config", "etc/gunicorn.conf.py", "meine_stadt_transparent.wsgi:application"]
