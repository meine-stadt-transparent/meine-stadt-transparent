# Open Source Ratsinformationssystem

[![Build Status](https://travis-ci.org/CatoTH/opensourceris.svg)](https://travis-ci.org/CatoTH/opensourceris)

Open Source RIS für Prototype Fund

## Development

Requirements: 
 - Python 3 with pip
 - A recent node version with npm
 - A webserver (nginx/apache)
 - For **elasticsearch**: docker and docker compose.
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


#### Elasticsearch

To use the [Elastic HQ](http://www.elastichq.org/), the graphical administration of elasticsearch, [download the
package](https://github.com/royrusso/elasticsearch-HQ/zipball/master) and unzip its content into
[elasticsearch_admin/static/elasticsearch](elasticsearch_admin/static/elasticsearch). If you hit problems regarding
memory, please have a look at this
[documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html#docker-cli-run-prod-mode).

```bash
wget https://github.com/royrusso/elasticsearch-HQ/zipball/master
unzip master
mv royrusso-elasticsearch-HQ-*/*
elasticsearch_admin/static/elasticsearch
rm -r royrusso-elasticsearch-HQ-*
rm master
```

#### LibOparl & GObject (gi)

GObject needs to be installed system-wide.

On Debian/Ubuntu, this can by done by:
```bash
# @TODO
```

On macOS:
```bash
brew install pygobject3 --with-python3
ln -s /usr/local/Cellar/pygobject3/3.26.0/lib/python3.6/site-packages/* /projectdir/venv/venv/lib/python3.6/site-packages/ # Replace 3.26.0 and projectdir by the real paths
```

After that, the command ``python3 -c "import gi"`` should not throw any errors within the virtualenv.

For liboparl, clone the [repository](https://github.com/OParl/liboparl) and follow the installation instructions. Until [#17](https://github.com/OParl/liboparl/pull/17) is merged, the ``resolve_url``-branch has to be checked out before compiling.

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

## Data model

The names of the models and the fields are highly inspired by the OParl standard.


## Shell commands

Import streets of a given city (identified by the german "Gemeindeschlüssel"):

```bash
./manage.py import-streets 05315000 1 # Gemeindeschlüssel von Köln, Body-ID 1
```

Import Open-Streetmap-Amenities of a given city (identified by the german "Gemeindeschlüssel"):

```bash
./manage.py import-amenities 05315000 school 1 # Gemeindeschlüssel von Köln, Amenity, Body-ID 1
```

Gemeindeschlüssel (examples):
- München: 09162000
- Augsburg: 09761000
- Neumarkt Sankt Veit: 09183129
- Köln: 05315000

## Installing liboparl

TODO

To access gi in a virtaulenv you have to do 

```bash 
ln -s /usr/lib/python3/dist-packages/gi venv/lib/python3.5/site-packages/
```