# Meine Stadt Transparent

[![Build Status](https://travis-ci.org/meine-stadt-transparent/meine-stadt-transparent.svg)](https://travis-ci.org/meine-stadt-transparent/meine-stadt-transparent)
[![Code Climate](https://codeclimate.com/github/meine-stadt-transparent/meine-stadt-transparent/badges/gpa.svg)](https://codeclimate.com/github/meine-stadt-transparent/meine-stadt-transparent)
[![Dependency Status](https://gemnasium.com/badges/github.com/meine-stadt-transparent/meine-stadt-transparent.svg)](https://gemnasium.com/github.com/meine-stadt-transparent/meine-stadt-transparent)

Meine Stadt Transparent is a council information system. Its current main focus is presenting data from offical German council information systems, so called "Ratsinforamtionssysteme". Those are imported using the [OParl](https://oparl.org) API, which can easily customized. You can even write your own importer for arbitrary data sources. 

The project is sponsored by the [Prototype Fund](https://prototypefund.de/).

![Logo of the Prototype Fund](etc/prototype-fund-logo.svg) ![Gefördert von Bundesministetrium für Bilduung und Forschung](etc/bmbf-logo.svg) ![Logo of the Open Knowledge Foundation Germany](etc/okfde-logo.svg)

## Quickstart with docker compose

Install [docker](https://docs.docker.com/engine/installation/) and [docker compose](https://docs.docker.com/compose/install/)

Copy `etc/env-docker-compose` to `.env-docker-compose` and change the setting to your desires.

Build the docker container (This will take some time):

```bash
docker-compose build
```

Start the whole stack.

```bash
docker-compose up
```

The database is still empty, so we need to run the migrations.

```bash
docker-compose run django ./manage.py migrate
```

Before starting, you'll need some data. You can either import (See the corresponding section below) or just use some dummy data.

```bash
docker-compose exec django ./manage.py loaddata mainapp/fixtures/initdata.json
```

You can now execute all the other commands from this readme by prepending them with `docker-compose exec django`. (Note for advanced users: The python in the virtualenv is configured as entrypoint.)

## Manual Setup

### Requirements:
 - Python 3 with pip
 - A recent node version with npm
 - A webserver (nginx or apache is recommended)
 - A Database (MariaDB is recommended, though anything that django supports should work)
 - A Java Runtime (for PDF Text extraction)
 - If you want to use elasticsearch: docker and docker compose.
 [Docker installation instructions](https://docs.docker.com/engine/installation/)

On Debian/Ubuntu:

```bash
sudo apt install python3-venv python3-pip python3-gi libmariadbclient-dev gettext openjdk-8-jre
```

Install dependencies

```bash
python3 -m venv venv # You can change the latter `venv` to whatever you like ..
source venv/bin/activate # .. but you also need to change it in this line 
pip install -r requirements.txt
npm install
```

Copy `etc/env-template` to `.env` and adjust the values. You can specify a different dotenv file with the `ENV_PATH` environment variable.

Configure your webserver. Example configurations:

 - [Apache](etc/apache.conf)
 - [nginx](etc/nginx.conf)
 
### pygobject (gi) and liboparl

This is currently only required to use the importer. You can skip it if you don't use the importer.

pygobject needs to be installed system-wide and only works with the system python. If you have any better solution for using a vala library in python we would be extremely happy to use it.

 -  Debian/Ubuntu:
    ```bash
    sudo apt install python3-gi
    ln -s /usr/lib/python3/dist-packages/gi venv/lib/python*/site-packages/
    ```

 -  macOS:
    ```bash
    brew install pygobject3 --with-python3
    # Replace 3.26.0 and projectdir by the real paths
    ln -s /usr/local/Cellar/pygobject3/3.26.0/lib/python3.6/site-packages/* /projectdir/venv/lib/python3.6/site-packages/ 
    ```

Try `python3 -c "import gi"` inside your virtualenv to ensure everything is working.

For liboparl, clone the [https://github.com/OParl/liboparl](https://github.com/OParl/liboparl) and follow the installation instructions.

Remember setting the environment variables or copy the typelib to an autodiscovery directory (whichever this is for your os). For Ubuntu 64-bit you need 

```bash
sudo cp OParl-0.2.typelib /usr/lib/x86_64-linux-gnu/girepository-1.0/OParl-0.2.typelib
```

### Development

The web server needs to be set up with an SSL certificate. You can use a [self-signed certificate](https://stackoverflow.com/a/10176685/3549270) for development.

Use `./manage.py runserver` to start the server.

### Production

Follow the [the official guide](https://docs.djangoproject.com/en/1.11/howto/deployment/). Unlike the guide, we recommend gunicorn over wsgi as gunicorn is much simpler to configure.

## Import

Import a whole RIS from an OParl-instance. See `--help` for options:

```bash
./manage.py importoparl https://www.muenchen-transparent.de/oparl/v1.0
```

Import streets of a given city (identified by the german "Gemeindeschlüssel"):

```bash
./manage.py importstreets 05315000 1 # Gemeindeschlüssel of Köln, Body-ID 1
```

Import OpenStreetMap-Amenities of a given city (identified by the german "Gemeindeschlüssel"):

```bash
./manage.py importamenities 05315000 school 1 # Gemeindeschlüssel of Köln, Amenity, Body-ID 1
```

Import the outer shape of a city from OpenStreetMap and write it into an existing body:
```bash
./manage.py importcityoutline 09162000 1 # Gemeindeschlüssel of Munich, Body-ID 1
```

Gemeindeschlüssel (examples):
- München: 09162000
- Augsburg: 09761000
- Neumarkt-Sankt Veit: 09183129
- Köln: 05315000
- Jülich: 05358024

### A complete installation for a city, starting from an empty database

To bootstrap a city, two pieces of information are required: the URL of the OParl-Endpoint, and (for now) the German "Gemeindeschlüssel".

The following example uses Jülich (Gemeindeschlüssel 05358024) as an example. The OParl-Importer uses the `--use-sternberg-workarounds` to mitigate issues with the current server-side implementations.

```bash
./manage.py migrate
./manage.py importbodies --use-sternberg-workarounds https://sdnetrim.kdvz-frechen.de/rim4240/webservice/oparl/v1/system
./manage.py importcityoutline 05358024 1
./manage.py importstreets 05358024 1
./manage.py importoparl --use-sternberg-workarounds https://sdnetrim.kdvz-frechen.de/rim4240/webservice/oparl/v1/system
```

## Important Commands

### Starting the development server

```bash
source venv/bin/activate
./manage.py migrate
./manage.py createsuperuser
./manage.py runserver
```

For compiling SCSS/JS automatically:

```bash
npm run watch
```

### Testing

Running the test cases:
```bash
ENV_PATH=./etc/env-test ./manage.py test
```

### Dummy data

The dummy data is used for the tests, but can also be used for developement.

Loading:

```bash
./manage.py loaddata mainapp/fixtures/initdata.json mainapp/fixtures/socialapps.json
```

Saving:

```bash
./manage.py dumpdata mainapp -e mainapp.UserProfile --indent 4 > mainapp/fixtures/initdata.json
```

### Elasticsearch

To reindex the elasticsearch index (requires elastic search to be enabled):

```bash
./manage.py search_index --rebuild
```

### Translating strings

```bash
cd mainapp/
django-admin makemessages -a
# translate django.po
django-admin compilemessages
```

### Setting up Social Login

To enable login via Twitter or Facebook, first you need to enable the functionality by adding these two lines to your .env-file:
```
SOCIALACCOUNT_USE_FACEBOOK=True
SOCIALACCOUNT_USE_TWITTER=True
```

Then follow the instructions at the [AllAuth-Page](http://django-allauth.readthedocs.io/en/latest/providers.html#facebook) to create the necessary tokens and register the tokens using the /admin/-backend.

### Notifying users about new documents

The following script is meant to be run as a cron job:
```bash
./manage.py notifyusers
``` 

However, for debugging purposes, it can be called stand alone, skipping the actual e-mail-sending and using a custom date range. The following commands dumps the search results of all users since 2017-09-10:
```bash
./manage.py notifyusers --debug --override-since 2017-09-10
``` 

### Creating a page with additional JS libraries

If we use a library on only one page and thus don't want to include it into the main JS-bundle (e.g. Isotope), this would the procedure:
- Normally install it using NPM
- Create a new entry JS script in [mainapp/assets/js](mainapp/assets/js). Require the library from there.
- Register this new entry point in the [webpack-configuration](etc/webpack.config.common.js).
- Load this new JS-file in a Django-template within the ``additional_js``-block using the ``render_bundle``-tag. (See [persons.html](mainapp/templates/mainapp/persons.html) for an example)

If a separate CSS-file is needed (e.g. in the case of fullcalendar), this would be the additional procedure to the one above (which is necessary):
- Create a new SCSS-file in [mainapp/assets/css](mainapp/assets/css).
- Require the SCSS-file from the corresponding JS entry script. This will automatically generate a compiled CSS-bundle with the name of the JS-bundle.
- Load this new CSS-file in a Django-template within the ``additional_css``-block using the ``render_bundle``-tag. (See [calendar.html](mainapp/templates/mainapp/calendar.html) for an example)

### Known Problems

If you hit problems regarding memory when starting elasticsearch, please have a look at this
[documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html#docker-cli-run-prod-mode).

If MySQL/MariaDB is to be used as a database backend, a Version of at least 5.7 (MySQL) or 10.2 (MariaDB) is needed,
with Barracuda being set as the default format for new InnoDB-Tables (default), otherwise you will run into errors about too long Indexes.
