FROM python:3.6
ENV PYTHONUNBUFFERED 1

RUN mkdir /app
WORKDIR /app

RUN curl -sL https://deb.nodesource.com/setup_6.x | bash - && \
    apt-get update && \
    apt-get install -y python-numpy python-scipy nodejs

# Python dependencies
COPY requirements.txt /app/requirements.txt
RUN python -m venv /app-env
ENV PATH "/app-env/bin:$PATH"
RUN pip install gunicorn
RUN pip install -r requirements.txt

# Javascript dependencies
COPY package.json /app/package.json
COPY package-lock.json /app/package-json.json
RUN npm install

# Build assets
COPY mainapp/assets /app/mainapp/assets
COPY etc /app/etc
RUN npm run build:dev

# Collect static files
COPY . /app/
COPY .env-docker-compose /config/.env
ENV ENV_PATH "/config/.env"
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["/app-env/bin/gunicorn", "meine_stadt_transparent.wsgi:application", "-w 2", "-b :8000", "--capture-output"]
