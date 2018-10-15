# Meine Stadt Transparent

[![Travis](https://img.shields.io/travis/meine-stadt-transparent/meine-stadt-transparent/master.svg?style=flat-square)](https://travis-ci.org/meine-stadt-transparent/meine-stadt-transparent)
[![Code Climate](https://codeclimate.com/github/meine-stadt-transparent/meine-stadt-transparent/badges/gpa.svg)](https://codeclimate.com/github/meine-stadt-transparent/meine-stadt-transparent)
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Fmeine-stadt-transparent%2Fmeine-stadt-transparent.svg?type=shield)](https://app.fossa.io/projects/git%2Bgithub.com%2Fmeine-stadt-transparent%2Fmeine-stadt-transparent?ref=badge_shield)
[![Docker Build Status](https://img.shields.io/docker/build/konstin2/meine-stadt-transparent.svg?style=flat-square)](https://hub.docker.com/r/konstin2/meine-stadt-transparent/)

Meine Stadt Transparent is a free council information system. Its current main focus is presenting data from offical German council information systems, so called "Ratsinforamtionssysteme". Those are imported using the [OParl](https://oparl.org) API, which can easily customized. You can even write your own importer for arbitrary data sources. 

Our sample live system using the data of the city [Jülich](https://www.juelich.de/) is available at: [https://meine-stadt-transparent.de/](https://meine-stadt-transparent.de/).

The project is sponsored by the [Prototype Fund](https://prototypefund.de/).

![Logo of the Prototype Fund](etc/prototype-fund-logo.svg) ![Gefördert von Bundesministetrium für Bilduung und Forschung](etc/bmbf-logo.svg) ![Logo of the Open Knowledge Foundation Germany](etc/okfde-logo.svg)

## About this project

Meine Stadt Transparent makes decision-making in city councils and administrations more transparent by providing easy access to information about the city council, including published documents, motions and meeting agendas. As a successor to Munich's [München Transparent](https://www.muenchen-transparent.de/), its aim is to be easily deployable for as many cities as possible.

It includes many features regarding data research and staying up to date, targeted both towards citizens and journalists:

- Information about city councillors, administrative organizations and meetings of the city council are provided.
- All published documents are searchable in a flexible manner, be it motions, resolutions, meeting agendas or protocols. The search supports both simple full-text searchs and flexible criteria-based filters.
- Documents are automatically searched for mentioned places. A map is provided indicating places that are mentioned. Thus, it is easy to identify documents that affect places in your living neighborhood.
- You can subscribe to topics / search expressions to get notified by e-mail, once new documents matching your query are published.
- It supports several ways of subscribing to new content: different kinds of RSS-feeds and subscribing to the meeting calendar using the iCal-format. 
- We try to make Meine Stadt Transparent accessible by everyone: the layout is responsive to provide a good experience on mobile device, and we follow accessibility standards (WCAG 2.0 AA, ARIA) as close as possible.

Meine Stadt Transparent is *not* a complete replacement for traditional council information systems, however: it focuses on displaying already published information to the public. It does not provide a user-accessible backend for content authoring. It relies on the availability of an API provided by a council information system backend. Currently, the open [Oparl-Standard](https://oparl.org/) is supported.

## Quickstart with docker compose

Install [docker ce](https://www.docker.com/community-edition) and [docker compose](https://docs.docker.com/compose/install/)

Before starting, you'll likely need to [adjust max_map_count on the host system](https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html#docker-cli-run-prod-mode).

Clone this repository and `cd` into it.

Then assemble everything with:

```bash
docker-compose pull
docker volume create --opt type=none --opt device=`pwd`/config --opt o=bind django_config
docker-compose up --no-build
```

Wait a until mariadb and elasticsearch have finshed starting. You should see `Cluster health status changed from [RED] to [YELLOW]` as last log message. Then open a new terminal for the following commands.

Then we can run the migrations:

```bash
docker-compose run django ./manage.py migrate
```

The database is still empty, so you'll need some data.

Option 1: Dummy data. Fast import and has all the relations.

```bash
docker-compose run django ./manage.py loaddata mainapp/fixtures/initdata.json
```

Option 2: Real data, which means this is slow. See the import section below for details.

```bash
docker-compose run django ./manage.py import [mycitiesname]
```

Meine Stadt Transparent is now running at [localhost:7000](http://localhost:7000).

**Before using this in production** set proper config values in `config/.env`. Make sure that you at least changed `REAL_HOST` and `SECRET_KEY` to proper values.

You can execute all the other commands from this readme by prepending them with `docker-compose exec django`. Note for advanced users: `poetry run` is configured as entrypoint.

To use this in production, you need to set up the two Cron-Jobs described below, to keep the data up to date and to send notifications to the users.

## Manual Setup

### Requirements

 - Python 3.5 or 3.6 with pip and [poetry](https://github.com/sdispater/poetry)
 - A recent node version (8 or 10) with npm (npm 6 is tested)
 - A webserver (nginx or apache is recommended)
 - A Database (MariaDB is recommended, though anything that django supports should work)
 - If you want to use elasticsearch, you either need [docker and docker compose](https://docs.docker.com/engine/installation/) or will have to [install elasticsearch 5.6 yourself](https://www.elastic.co/guide/en/elasticsearch/reference/5.6/_installation.html)

On Debian/Ubuntu:

```bash
sudo apt install python3-pip python3-venv python3-gi python3-dev nodejs json-glib-1.0 gir1.2-json-1.0 \
    git libmysqlclient-dev libmagickwand-dev poppler-utils tesseract-ocr
```

Install dependencies. 

```bash
poetry config settings.virtualenvs.in-project true # This is not mandatory, yet quite useful
poetry install 
npm install
```

Activate the virtualenv created by poetry. You either need to run this in your shell before running any other python command or prefix any python command with `poetry run`.

```bash
poetry shell 
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
    ln -s /usr/lib/python3/dist-packages/gi .venv/lib/python*/site-packages/
    ```

 -  macOS:
    ```bash
    brew install pygobject3 --with-python3
    # Replace 3.26.0 and projectdir by the real paths
    ln -s /usr/local/Cellar/pygobject3/3.26.0/lib/python3.6/site-packages/* .venv/lib/python3.6/site-packages/ 
    ```

Try `python3 -c "import gi"` inside your virtualenv to ensure everything is working.

For liboparl, clone the [https://github.com/OParl/liboparl](https://github.com/OParl/liboparl) and follow the installation instructions. Be sure to use `--prefix=/usr --buildtype=release` on `meson`.

### Production

The following steps are only required when you want to deploy the site to production. For development, see the corresponding section below

 ```bash
npm run build:prod
npm run build:email
./manage.py collectstatic
 ```

Follow the [the official guide](https://docs.djangoproject.com/en/1.11/howto/deployment/). Unlike the guide, we recommend gunicorn over wsgi as gunicorn is much simpler to configure.

The site is now fully configured :tada:

## Import

### The easy way

```bash
./manage.py import [mycitiesname]
```

You need to use the official German name with the right capitalization, e.g. `München` or `Jülich` and not `münchen` or `Juelich`. The [service](https://www.wikidata.org) we're using is a bit picky on those names.

This script will eventually finish and tell you to add some lines to the dotenv. After that you can always do a new
import with

```bash
./manage.py importoparl
```

### The manual way

Import a whole RIS from an OParl-instance. See `--help` for options:

First of all, we need to import the Body in our database from the OParl backend
```bash
./manage.py importbodies https://www.muenchen-transparent.de/oparl/v1.0
```

Next you'll need the German "Gemeindeschlüssel", which is a 8 letter value that each communality has. You might find your's with

```bash
./manage.py citytoags [mycitiesname]
```

Examples:
- München: 09162000
- Augsburg: 09761000
- Neumarkt-Sankt Veit: 09183129
- Köln: 05315000
- Jülich: 05358024

In addition to the Gemeindeschlüssel, you well need the "Body-ID", the primary key of the database record corresponding to the main body. If the database has been newly created, this will usually be "1".

Then import the streets of that city:

```bash
./manage.py importstreets 05315000 1 # Gemeindeschlüssel of Köln, Body-ID 1
```

Import OpenStreetMap-Amenities of a given city (Not required yet):

```bash
./manage.py importamenities 05315000 school 1 # Gemeindeschlüssel of Köln, Amenity, Body-ID 1
```

Import the outer shape of a city from OpenStreetMap and write it into an existing body:

```bash
./manage.py importcityoutline 09162000 1 # Gemeindeschlüssel of Munich, Body-ID 1
```

Now we can import the actual data from the OParl backend. This is going to take quite a while:

```bash
./manage.py importoparl https://www.muenchen-transparent.de/oparl/v1.0
```

Now two variables have to be set in the ``.env``-File:
- ``SITE_DEFAULT_BODY``: The Body-ID from above
- ``SITE_DEFAULT_ORGANIZATION``: The ID of the central organization of the city council in the ``mainapp_organization`` table

Now the site should be working. If the "Latest Documents"-Section on the home page shows random old entries after the initial import, you can try to fix the dates with the following command:

```bash
./manage.py fix-dates 2018-01-01 2000-01-01 # The date of the initial import and a fallback date far in the past so files without determinable date show up last
./manage.py search_index --rebuild # Push the changed data to ElasticSearch
```

### Using the OParl Importer programmatically

`importer.oparl_import.OParlImport` has all the top level methods which are e.g. used by the import commands. It inherits `importer.oparl_objects.OParlObjects` which has methods to import the individual OParl objects except System. You need to pass the constructor an option set based on `importer.oparl_helper.default_options` with the correct value for `entrypoint` set. Note that error handling with mutlithreading and liboparl is weird to non-functional.

### A complete installation for a city, starting from an empty database

To bootstrap a city, two pieces of information are required: the URL of the OParl-Endpoint, and (for now) the German "Gemeindeschlüssel".

The following example uses Jülich (Gemeindeschlüssel 05358024) as an example. Internally the OParl importer will use Sternberg specific workarounds to mitigate errors in their implementations.

OParl-related entries in the ``.env``-file:
```txt
OPARL_ENDPOINT=https://sdnetrim.kdvz-frechen.de/rim4240/webservice/oparl/v1/system
```

Shell commands:
```bash
./manage.py importbodies
./manage.py importcityoutline 05358024 1
./manage.py importstreets 05358024 1
./manage.py importoparl
```

### Importing only a single object

Instead of crawling the whole API, it is possible to update only one specific item using the ``importanything``-command. You will need to specify the entrypoint like always and the URL of the actual OParl-Object. Here are examples how to import a person, a paper and a meeting:
```bash
./manage.py importanything https://sdnetrim.kdvz-frechen.de/rim4240/webservice/oparl/v1/body/1/person/4933
./manage.py importanything https://sdnetrim.kdvz-frechen.de/rim4240/webservice/oparl/v1/body/1/paper/53584
./manage.py importanything https://sdnetrim.kdvz-frechen.de/rim4240/webservice/oparl/v1/body/1/meeting/7298
```

### Cronjobs

```bash
./manage.py cron
```

This will clear the oparl cache, import changed objects from the oparl api and then notify the users

## Customization

### Overriding templates and styles

You can easily override templates and add custom styles, e.g. for matching the corporate design of a specific city.

Two examples are bundled with this repository:
- [juelich_transparent](customization_examples/juelich_transparent): Only the [contact form](mainapp/templates/info/contact.html) is overridden
- [bedburg_transparent](customization_examples/bedburg_transparent): The contact form is overriden and a custom style sheet is provided. 

You can easily add your own customizations by putting them into a folder inside `customizations`. Copying over one of the examples should by a good starting point.

To override a templates, set `TEMPLATE_DIRS` in ``.env`` to the ``templates``-folder within the city directory, e.g. ``TEMPLATE_DIRS=customization/juelich_transparent/templates``

The following parts are required to change styles or javascript:
  - A ``webpack.config.js`` file registering an entry point for Webpack. The entry point needs to point to a js-File. Note that the paths in that file are realtive to [etc](etc).
  - The js File, usually ``assets/js/mycity-main.js``. This file includes the main SCSS file with an ES6 import.
  - The SCSS-File, usually ``assets/css/mainapp-mycity.scss``. This file includes the main [mainapp.scss](mainapp/assets/css/mainapp.scss), but can define its own variables and styles as well. It will be compiled to a regular CSS file of the same base filename.
  - The new CSS-File needs to be registered in the ``.env``-file, e.g. ``TEMPLATE_MAIN_CSS=mainapp-mycity``

Hints:
 - Do not modify our files without creating a pull request. You'll have huge problems updating otherwise. Also put your files in a version control system (i.e. git).
 - Keep the name of the export, the name of the main js file and the name of the main scss file identical to avoid confusion.
 - templates are written in the [django template language](https://docs.djangoproject.com/en/1.11/topics/templates/#the-django-template-language).
 - Localization does also work for custom templates. With `./manage.py makemessages -a` you create or update into a file called `locale/de/LC_MESSAGES/django.po` in your custom folder. Translate your strings there and compile them with `./manage.py compilemessages --locale de`. 

##### Embedding external resources / CSP

If you modify templates as described above and want to embed resources hosted on another domain (for example to embed images, web-fonts, or a tracking tool), you have to whitelist the used domains, as our Content Security Policy ([CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)) will prevent them from being loaded otherwise. The following configuration settings are supported for that reason:

```
CSP_EXTRA_SCRIPT=www.example.org,'sha256-QOPA8zHkrz5+pN4Af9GXK6m6mW7STjPY13tS3Z3xLTU=' # The latter one is for whitelisting inline-scripts
CSP_EXTRA_IMG=www.example.org
```

### Sanitizing values coming from an OParl-API

Sometimes, redundant, unnecessary or unnormalized information comes from an API that you might want to clean up during the import. To do that on an per-instance-basis without the need to patch the importer itself, we provide hooks you can attach custom sanitize-callbacks to. The callbacks are simple Python-scripts that take an object as input and return it in a sanitized version.

The following steps are required to register a sanitize-hook:
- Create a python script that will hold contain the functions, e.g. ``customization/import_hooks.py``. You can use [import_hooks.py](customization_examples/juelich_transparent/import_hooks.py) as an example. Please note that the directory needs to contain a ``__init__.py``-file.
- Register the script in your local ``.env``-file like this: ``CUSTOM_IMPORT_HOOKS=customization.import_hooks``
- Please refer to our [example script](customization_examples/juelich_transparent/import_hooks.py) to see which callbacks are available and how to write one.

## External Services

For some functionality, we rely on external web services. Most of them are optional, but can improve the quality and reliability of this system. To use them, you will need to create an account and set the credentials in the ``.env``file.

### Facebook, Twitter

To enable login via Twitter or Facebook, o create an app in the corresponding developer portal. See the [AllAuth-Page](http://django-allauth.readthedocs.io/en/latest/providers.html#facebook) for details.

For twitter, you'll also need [https://stackoverflow.com/a/32852370/3549270](https://stackoverflow.com/a/32852370/3549270) or users will be prompted to enter an email adress after login.

For facebook, you'll need to go to `https://developers.facebook.com/apps/[your appp id]/fb-login/settings/` and add the site's url in "valid oauth redirect urls".

You can then activate them in your `.env`-file:

```
SOCIALACCOUNT_USE_FACEBOOK=True
FACEBOOK_CLIENT_ID=[app id]
FACEBOOK_SECRET_KEY=[app secret]
```

```
SOCIALACCOUNT_USE_TWITTER=True
TWITTER_CLIENT_ID=[app id]
TWITTER_SECRET_KEY=[app secret]
```

After changing any token, use `./manage.py register_social_accounts` to apply the changes.

### Mapbox

By default, the map uses the tiles provided by [OpenStreetMap](https://wiki.openstreetmap.org/wiki/Standard_tile_layer). However, for production use, it is recommended to use another provider. For now, we support [Mapbox](https://www.mapbox.com/). To use it, you need to sign up for an account, choose a map style and add the following information to the ``.env``-file:

```
MAP_TILES_PROVIDER=Mapbox
MAP_TILES_MAPBOX_TOKEN=pk....
MAP_TILES_URL=https://api.mapbox.com/styles/v1/username/stylename/tiles/256/{z}/{x}/{y}{highres}?access_token={accessToken}
```

### Microsoft Azure: OCR

This is optional if you want to use OCR for extracting the text of scanned documents. Set up a Azure account and add a [Computer Vision](https://azure.microsoft.com/en-us/try/cognitive-services/?api=computer-vision)-Resource (part of Cognitive Services). Add the API Key to the ``.env``-File:

```
OCR_AZURE_KEY=...
```

### Open Cage Data: Geo extraction

By default, we use [Nominatim](https://wiki.openstreetmap.org/wiki/Nominatim) to resolve addresses to coordinates. In case you want to switch to the [OpenCage Geocoder](https://geocoder.opencagedata.com/), you can register it by adding these credentials:

```
GEOEXTRACT_ENGINE=OpenCageData
OPENCAGEDATA_KEY=...
```

### Mailjet

By default, we send e-mails using the local SMTP server. [Mailjet](https://dev.mailjet.com/) can be set up as an alternative for sending e-mails:

```
DEFAULT_FROM_EMAIL=info@meine-stadt-transparent.de
MAIL_PROVIDER=Mailjet
MAILJET_API_KEY=...
MAILJET_SECRET_KEY=...
```

The e-mail-configuration can be tested using the following command line call, which sends a test e-mail to the given e-mail-address:

```bash
./manage.py test-email test@example.org
```

## Development

The web server needs to be set up with an SSL certificate. You can use a [self-signed certificate](https://stackoverflow.com/a/10176685/3549270) for development.

### Assets

You can either build the assets once ...
```bash
npm run build:dev
npm run build:email
```

... or rebuild after every change
```bash
npm run watch
```

Run the migrations and create an admin user
```bash
./manage.py migrate
```

Start the actual server
```bash
./manage.py runserver
```

### Testing

Run the test cases:

```bash
./manage.py test
```

There's a tox config to ensure 3.5 and 3.6 compatibility which can be run with `tox`.

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
django-admin makemessages -a
# translate django.po
django-admin compilemessages
```

### Notifying users about new documents

The following script is meant to be run as a cron job:
```bash
./manage.py notifyusers
```

However, for debugging purposes, it can be called stand alone, skipping the actual e-mail-sending and using a custom date range. The following commands dumps the search results of all users since 2017-09-10:
```bash
./manage.py notifyusers --debug --override-since 2017-09-10
```

### OCR'ing documents

Currently, OCR'ing documents is not done automatically, as this operation is being billed per execution. So for now, it is done manually on demand. The following commands are available to ocr a single file, or to ocr all files with no recognized text:

```bash
# OCR all empty files:
./manage.py ocr-file --empty
# OCR an individual file:
./manage.py ocr-file --id 23
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

### E-Mail-Notifications

The templates for the e-mail-notifications are created using [HEML](https://heml.io/). So we don't edit the HTML/Django-templates like [user-alert.html](mainapp/templates/email/user-alert.html) directly, but the source .heml-files like [user-alert.heml](mainapp/assets/email/user-alert.heml) and compile them using:
```bash
npm run build:email
```

## Known Problems

If you hit problems regarding memory when starting elasticsearch, please have a look at this
[documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html#docker-cli-run-prod-mode).

If MySQL/MariaDB is to be used as a database backend, a Version of at least 5.7 (MySQL) or 10.2 (MariaDB) is needed,
with Barracuda being set as the default format for new InnoDB-Tables (default), otherwise you will run into errors about too long Indexes.


## License

This software is published under the terms of the MIT license. The json files under `mainapp/testdata/oparl` are adapted from the oparl project and licensed under CC-BY-SA-4.0. The license of the included animal pictures `mainapp/testdata/oparl` are CC0 and CC-BY-SA Luigi Rosa. The redistribution of `etc/Donald Knuth - The Complexity of Songs.pdf` is explicitly allowed in its last paragraph. 

[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Fmeine-stadt-transparent%2Fmeine-stadt-transparent.svg?type=large)](https://app.fossa.io/projects/git%2Bgithub.com%2Fmeine-stadt-transparent%2Fmeine-stadt-transparent?ref=badge_large)
