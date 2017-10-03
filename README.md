# Open Source Ratsinformationssystem

[![Build Status](https://travis-ci.org/CatoTH/opensourceris.svg)](https://travis-ci.org/CatoTH/opensourceris)

Open Source RIS für Prototype Fund

![Logo of the Prototype Fund](etc/prototype-fund-logo.svg) ![Gefördert von Bundesministetrium für Bilduung und Forschung](etc/bmbf-logo.svg) ![Logo of the Open Knowledge Foundation Germany](etc/okfde-logo.svg)

## Development

Requirements: 
 - Python 3 with pip
 - A recent node version with npm
 - A webserver (nginx/apache)
 - If you want to use elasticsearch: docker and docker compose.
 [Docker installation instructions](https://docs.docker.com/engine/installation/)

### Installing the project

Create a virtualenv at `venv`. Add a local domain https://opensourceris.local/ with self-signed certificates in your
webserver which redirects to localhost:8080

```bash
pip install -r requirements.txt
npm install
```

The web server needs to be set up with a (self-signed) SSL certificate. Example configurations for some web servers:
 - [Apache](etc/apache.conf)
 - [nginx](etc/nginx.conf)


#### Elastic HQ

To use the [Elastic HQ](http://www.elastichq.org/), the graphical administration of elasticsearch, [download the
package](https://github.com/royrusso/elasticsearch-HQ/zipball/master) and unzip its content into
[elasticsearch_admin/static/elasticsearch](elasticsearch_admin/static/elasticsearch). If you hit problems regarding
memory, please have a look at this
[documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html#docker-cli-run-prod-mode).

All in one:

```bash
wget https://github.com/royrusso/elasticsearch-HQ/zipball/master
unzip master
mv royrusso-elasticsearch-HQ-*/*
elasticsearch_admin/static/elasticsearch
rm -r royrusso-elasticsearch-HQ-*
rm master
```

#### pygobject (gi) and liboparl

This is currently only required to use the importer.

GObject needs to be installed system-wide.

 -  Debian/Ubuntu:
    ```bash
    sudo apt install python3-gi
    ln -s /usr/lib/python3/dist-packages/gi venv/lib/python*/site-packages/
    ```

 -  macOS:
    ```bash
    brew install pygobject3 --with-python3
    ln -s /usr/local/Cellar/pygobject3/3.26.0/lib/python3.6/site-packages/* /projectdir/venv/lib/python3.6/site-packages/ # Replace 3.26.0 and projectdir by the real paths
    ```

Try `python3 -c "import gi"` inside your virtualenv to ensure everything is working.

For liboparl, clone the [https://github.com/OParl/liboparl](https://github.com/OParl/liboparl) and follow the installation instructions. Until
[#17](https://github.com/OParl/liboparl/pull/17) is merged, the ``resolve_url``-branch has to be checked out before
compiling. Remember setting the environment variables or copy the typelib to an autodiscovery directory (whichever this
is for your os)

### Starting the development server

```bash
docker-compose up # For elasticsearch
```


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
./manage.py test
```

### Important URLs:

- https://opensourceris.local/
- https://opensourceris.local/admin/
- https://opensourceris.local/elasticsearch_admin/ (default password for elasticsearch: ``elastic`` / ``changeme``)
- https://docs.google.com/document/d/1Qib4wBvavB8PcJ3LJ45wmNk6vFAXfpQ-2zi1Oal1rIY/edit# : Interne To Dos

## Shell commands

### Dummy Data

To load the dummy data for development:

```bash
./manage.py loaddata mainapp/fixtures/initdata.json mainapp/fixtures/socialapps.json
```

To reindex the elasticsearch index:

```bash
./manage.py search_index --rebuild
```

To save the modified dummy data

```bash
./manage.py dumpdata mainapp -e mainapp.UserProfile --indent 4 > mainapp/fixtures/initdata.json
```

### Translating strings

```bash
cd mainapp/
django-admin makemessages -a
# translate django.po
django-admin compilemessages
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

### Import

Import a whole RIS from an OParl-instance. See `--help` for options
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
- Neumarkt Sankt Veit: 09183129
- Köln: 05315000

## Data model

The names of the models and the fields are highly inspired by the OParl standard.
