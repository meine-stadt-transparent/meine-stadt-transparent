# TODO: Get liboparl published on docker hub and copy from that image instead
FROM ubuntu:17.10
RUN apt-get update
RUN apt install -y valac valadoc gobject-introspection libjson-glib-dev libgirepository1.0-dev meson gettext git

RUN git clone https://github.com/oparl/liboparl
RUN mkdir liboparl/build
WORKDIR /liboparl/build
RUN meson ..
RUN ninja
RUN ninja install
RUN cp OParl-0.*.typelib /usr/lib/x86_64-linux-gnu/girepository-1.0/

# We can't use the python image because pygobject only works with system python
FROM ubuntu:16.04
ENV PYTHONUNBUFFERED 1
ENV LANG C.UTF-8

RUN mkdir /app
WORKDIR /app

RUN apt-get update && \
    apt-get install -y curl && \
    curl -sL https://deb.nodesource.com/setup_6.x | bash - && \
    apt-get install -y python3-numpy python3-scipy nodejs python3-pip python3-venv python3-gi \
    json-glib-1.0  gir1.2-json-1.0 git libmariadbclient-dev

# liboparl
COPY --from=0 /usr/local/share/locale/en_US/LC_MESSAGES/liboparl.mo /usr/local/share/locale/en_US/LC_MESSAGES/liboparl.mo
COPY --from=0 /usr/local/share/locale/de_DE/LC_MESSAGES/liboparl.mo /usr/local/share/locale/de_DE/LC_MESSAGES/liboparl.mo
COPY --from=0 /usr/local/lib/x86_64-linux-gnu/liboparl-0.2.so /usr/local/lib/x86_64-linux-gnu/liboparl-0.2.so
COPY --from=0 /usr/lib/x86_64-linux-gnu/girepository-1.0/OParl-0.2.typelib /usr/lib/x86_64-linux-gnu/girepository-1.0/OParl-0.2.typelib

# Python dependencies
COPY requirements.txt /app/requirements.txt
RUN python3 -m venv /app-env
RUN ln -s /usr/lib/python3/dist-packages/gi /app-env/lib/python*/site-packages/
# Activate the virtualenv in a docker compatible way
ENV PATH "/app-env/bin:$PATH"
RUN pip install --upgrade pip
RUN pip install gunicorn
# The default locale breaks python 3 < python 3.7. https://bugs.python.org/issue28180
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

ENTRYPOINT ["/app-env/bin/python"]
CMD ["/app-env/bin/gunicorn", "meine_stadt_transparent.wsgi:application", "-w 2", "-b :8000", "--capture-output"]
