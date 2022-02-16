# Import

We support importing data from an oparl api.

## The easy way

```
./manage.py import Springfield
```

You need to use the official German name with the right capitalization, e.g. `München` or `Jülich` and not `münchen` or `Juelich`. The [service](https://www.wikidata.org) we're using is a bit picky with those names. The script will tell you to add some lines to the dotenv at the beginning and in the end (and in the logs).

If you've added the cron job, the data will automatically be updated. Otherwise you can always do a manual update with

```
./manage.py import_update
```

## The manual way

We import the data in four steps:

* Import the body with some metadata
* Get the bulk of data from the oparl api
* Import the data to the database
* Download and analyse the files

All commands have more options available through `--help`.

## Step 1: Body

For the first step, you can use the heuristic from `import_body` with the case-sensitive cityname or the body id:

```
./manage.py import_body Springfield
```

or

```
./manage.py import_body https://oparl.example.org/v1/body/Springfield
```

If that worked, go to step 2. If you don't to use the heuristic, pass `--manual`:

```
./manage.py import_body --manual https://oparl.example.org/v1/body/Springfield
```

You'll need to find out the German "Amtliche Gemeindeschlüssel", which is an 8 letter value that each communality has. You might find yours with

```
./manage.py city_to_ags Springfield
```

Examples:

- München: 09162000
- Augsburg: 09761000
- Neumarkt-Sankt Veit: 09183129
- Köln: 05315000
- Jülich: 05358024

The full list can be found at [in this pdf](https://www.riserid.eu/data/user_upload/downloads/info-pdf.s/Diverses/Liste-Amtlicher-Gemeindeschluessel-AGS-2015.pdf) ([archive](https://web.archive.org/web/20190112120729/https://www.riserid.eu/data/user_upload/downloads/info-pdf.s/Diverses/Liste-Amtlicher-Gemeindeschluessel-AGS-2015.pdf)).

The last `import_body` has printed the body-id, the primary key of the database record corresponding to the body. If the database has been newly created, this will usually be "1". Set `SITE_DEFAULT_BODY` in you `.env` to that id.

Import the streets of that city:

```
./manage.py import_streets 1 --ags 05315000 # Gemeindeschlüssel of Köln, Body-ID 1
```

Import OpenStreetMap-Amenities of a given city (Not required yet):

```
./manage.py import_amenities school 1 --ags 05315000 # Gemeindeschlüssel of Köln, Amenity, Body-ID 1
```

Import the outer shape of a city from OpenStreetMap:

```
./manage.py import_outline 1 --ags 09162000 # Gemeindeschlüssel of Munich, Body-ID 1
```

## Step 2: Fetch the data

Now we can import the actual data from the OParl backend. This is going to take quite a while because those servers are really slow:

```
./manage.py import_fetch
```

## Step 3: Import the data

Import the loaded data into the database:

```
./manage.py import_objects
```

## Step 4: Load and analyse the files

We've now got a fully working instance, just without files. Their import speed is limited by the cpu-intensive analysis:

```
./manage.py import_files
```

## Troubleshooting

Since downloading the data from the oparl api can be very slow, you can dump the cache import into a file once finished and use it to retry the much quicker import.

Export:

```
./manage.py dumpdata importer -o reinickendorf-importer.json
```

`flush` the database, import:

```
./manage.py loaddata importer-data.json
./manage.py set_cache_to_reimport
```

After that you can continue from `import_body --manual`.

## Importing only a single object

Instead of crawling the whole API, it is possible to update only one specific item using the `import_anything`-command. You will need to specify the urlof the OParl-Object. Here are examples how to import a person, a paper and a meeting:

```
./manage.py import_anything https://sdnetrim.kdvz-frechen.de/rim4240/webservice/oparl/v1/body/1/person/4933
./manage.py import_anything https://sdnetrim.kdvz-frechen.de/rim4240/webservice/oparl/v1/body/1/paper/53584
./manage.py import_anything https://sdnetrim.kdvz-frechen.de/rim4240/webservice/oparl/v1/body/1/meeting/7298
```

## Sanitizing values coming from an OParl-API

Sometimes, redundant, unnecessary or unnormalized information comes from an API that you might want to clean up during the import. To do that on an per-instance-basis without the need to patch the importer itself, we provide hooks you can attach custom sanitize-callbacks to. The callbacks are simple Python-scripts that take an object as input and return it in a sanitized version.

The following steps are required to register a sanitize-hook:

- Create a python script that will hold contain the functions, e.g. ``customization/import_hooks.py``. You can use [import_hooks.py](../customization_examples/juelich_transparent/import_hooks.py) as an example. Please note that the directory needs to contain a ``__init__.py``-file.
- Register the script in your local ``.env``-file like this: ``CUSTOM_IMPORT_HOOKS=customization.import_hooks``
- Please refer to our [example script](../customization_examples/juelich_transparent/import_hooks.py) to see which callbacks are available and how to write one.
