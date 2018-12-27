## Import

We support importing data from an oparl api.

### The easy way

```
./manage.py import Springfield
```

You need to use the official German name with the right capitalization, e.g. `München` or `Jülich` and not `münchen` or `Juelich`. The [service](https://www.wikidata.org) we're using is a bit picky on those names.

This script will eventually finish and tell you to add some lines to the dotenv. After that you can always do a new
import with

```
./manage.py importoparl
```

### The manual way

Either add an `OPARL_ENDPOINT` entry to your ``.env``-file with the url of the oparl api, or pass it to the commands with `--entrypoint=`:

```
--entrypoint==https://sdnetrim.kdvz-frechen.de/rim4240/webservice/oparl/v1/system
```

All commands have more options available through `--help`:

First of all, we need to import the Body in our database from the OParl backend

```
./manage.py importbodies
```

Next you'll need the German "Gemeindeschlüssel", which is a 8 letter value that each communality has. You might find your's with

```
./manage.py citytoags Springfield
```

Examples:
- München: 09162000
- Augsburg: 09761000
- Neumarkt-Sankt Veit: 09183129
- Köln: 05315000
- Jülich: 05358024

In addition to the Gemeindeschlüssel, you well need the "Body-ID", the primary key of the database record corresponding to the main body. If the database has been newly created, this will usually be "1".

Then import the streets of that city:

```
./manage.py importstreets 05315000 1 # Gemeindeschlüssel of Köln, Body-ID 1
```

Import OpenStreetMap-Amenities of a given city (Not required yet):

```
./manage.py importamenities 05315000 school 1 # Gemeindeschlüssel of Köln, Amenity, Body-ID 1
```

Import the outer shape of a city from OpenStreetMap and write it into an existing body:

```
./manage.py importcityoutline 09162000 1 # Gemeindeschlüssel of Munich, Body-ID 1
```

Now we can import the actual data from the OParl backend. This is going to take quite a while:

```
./manage.py importoparl https://www.muenchen-transparent.de/oparl/v1.0
```

Now two variables have to be set in the ``.env``-File:
 * ``SITE_DEFAULT_BODY``: The Body-ID from above
 * ``SITE_DEFAULT_ORGANIZATION``: The ID of the central organization of the city council in the ``mainapp_organization`` table

Now the site should be working. If the "Latest Documents"-Section on the home page shows random old entries after the initial import, you can try to fix the dates with the following command:

```
./manage.py fix-dates 2018-01-01 2000-01-01 # The date of the initial import and a fallback date far in the past so files without determinable date show up last
./manage.py search_index --rebuild # Push the changed data to ElasticSearch
```

### Importing only a single object

Instead of crawling the whole API, it is possible to update only one specific item using the ``importanything``-command. You will need to specify the entrypoint like always and the URL of the actual OParl-Object. Here are examples how to import a person, a paper and a meeting:

```
./manage.py importanything https://sdnetrim.kdvz-frechen.de/rim4240/webservice/oparl/v1/body/1/person/4933
./manage.py importanything https://sdnetrim.kdvz-frechen.de/rim4240/webservice/oparl/v1/body/1/paper/53584
./manage.py importanything https://sdnetrim.kdvz-frechen.de/rim4240/webservice/oparl/v1/body/1/meeting/7298
```

### Sanitizing values coming from an OParl-API

Sometimes, redundant, unnecessary or unnormalized information comes from an API that you might want to clean up during the import. To do that on an per-instance-basis without the need to patch the importer itself, we provide hooks you can attach custom sanitize-callbacks to. The callbacks are simple Python-scripts that take an object as input and return it in a sanitized version.

The following steps are required to register a sanitize-hook:
- Create a python script that will hold contain the functions, e.g. ``customization/import_hooks.py``. You can use [import_hooks.py](../customization_examples/juelich_transparent/import_hooks.py) as an example. Please note that the directory needs to contain a ``__init__.py``-file.
- Register the script in your local ``.env``-file like this: ``CUSTOM_IMPORT_HOOKS=customization.import_hooks``
- Please refer to our [example script](../customization_examples/juelich_transparent/import_hooks.py) to see which callbacks are available and how to write one.

### Using the OParl Importer programmatically

`importer.oparl_import.OParlImport` has all the top level methods which are e.g. used by the import commands. It inherits `importer.oparl_objects.OParlObjects` which has methods to import the individual OParl objects except System. You need to pass the constructor an option set based on `importer.oparl_helper.default_options` with the correct value for `entrypoint` set. Note that error handling with mutlithreading and liboparl is weird to non-functional.
