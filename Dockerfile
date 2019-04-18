FROM ubuntu:18.04

ENV PYTHONUNBUFFERED 1
# The default locale breaks python 3 < python 3.7. https://bugs.python.org/issue28180
ENV LANG C.UTF-8

RUN apt-get update && \
    apt-get install -y curl gnupg && \
    curl -sL https://deb.nodesource.com/setup_10.x | bash - && \
    apt-get install -y python3-pip python3-venv python3-dev \
    nodejs git libmysqlclient-dev libmagickwand-dev poppler-utils tesseract-ocr libssl-dev gettext && \
    apt-get autoremove -y && \
    apt-get clean

# Setup the python part

COPY pyproject.toml /app/pyproject.toml
COPY poetry.lock /app/poetry.lock
WORKDIR /app

RUN pip3 install --upgrade poetry \
    && poetry config settings.virtualenvs.in-project true \
    && poetry install --no-dev
COPY . /app/

ENV NODE_ENV production

RUN etc/docker-init.sh

EXPOSE 8000

USER www-data

ENTRYPOINT ["poetry", "run"]
CMD ["gunicorn", "meine_stadt_transparent.wsgi:application", "-w 2", "-b :8000", "--capture-output"]
