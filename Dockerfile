# We just need some files from this image
FROM oparl/liboparl:0.4.0
# We can't use the python image because pygobject only works with system python
FROM ubuntu:16.04

ENV PYTHONUNBUFFERED 1
# The default locale breaks python 3 < python 3.7. https://bugs.python.org/issue28180
ENV LANG C.UTF-8
ENV ENV_PATH "/config/.env"

RUN mkdir /app
WORKDIR /app

RUN apt-get update && \
    apt-get install -y curl && \
    curl -sL https://deb.nodesource.com/setup_8.x | bash - && \
    apt-get install -y python3-pip python3-venv python3-gi python3-dev nodejs json-glib-1.0 gir1.2-json-1.0 \
    git libmysqlclient-dev libmagickwand-dev poppler-utils tesseract-ocr && \
    apt-get autoremove -y && \
    apt-get clean

# liboparl
COPY --from=0 /usr/share/locale/en_US/LC_MESSAGES/liboparl.mo /usr/share/locale/en_US/LC_MESSAGES/liboparl.mo
COPY --from=0 /usr/share/locale/de_DE/LC_MESSAGES/liboparl.mo /usr/share/locale/de_DE/LC_MESSAGES/liboparl.mo
COPY --from=0 /usr/lib/x86_64-linux-gnu/liboparl-0.4.so /usr/lib/x86_64-linux-gnu/liboparl-0.4.so
COPY --from=0 /usr/lib/x86_64-linux-gnu/girepository-1.0/OParl-0.4.typelib /usr/lib/x86_64-linux-gnu/girepository-1.0/OParl-0.4.typelib

COPY . /app/

RUN /app/etc/docker-init.sh

EXPOSE 8000

USER www-data

ENTRYPOINT ["poetry", "run"]
CMD ["gunicorn", "meine_stadt_transparent.wsgi:application", "-w 2", "-b :8000", "--env", "ENV_PATH=/config/.env", "--capture-output"]
