# Changelog

Please see the [Readme](Readme.md#Update]) on what commands to run after an update.

## v0.2.12 - Unreleased

 * Add `SENTRY_TRACES_SAMPLE_RATE` for the sentry integration (https://docs.sentry.io/platforms/python/guides/django/performance/).
 * The gunicorn config is now in `etc/gunicorn.conf.py`, which can be overwritten by mounting a different file into the container
 * The `delete_file` command now prevents a file from getting reimported with the json import

## v0.2.11

  * Added a `delete_file` command, which remove the file from minio

## v0.2.10

 * webpack 5
 * Added a somacos loader
 * `SSL_NO_VERIFY` setting to hack around broken ssl configurations
 * Fixed the mapbox default url

## v0.2.9

 * The json import format was update to version 4.
 * Replaced the node tool osmtogeojson with the python osm2geojson so that the runtime doesn't need node anymore. This also removes a few outdated dependencies.
 * Some small UI changes to incorporate user feedback

## 0.2.8

Note: Please rebuild the search index after installing this version (`./manage.py search_index --rebuild`)

 * Both importer now have a better heuristics for determining the date of a paper. Additionally, the result order should now be more reasonable.
 * Updated the json importer to format version 3
 * Fixed a regression with meeting without end from 0.2.7
 * The ics export has an html description (which is used e.g. by google calendar and outlook) which includes a link to the meeting.

## 0.2.7

 * `manage.py import_json` now by defaults send notifications, this can be disabled with `--no-notify-users`
 * Handle missing elasticsearch or minio more gracefully
 * Fixed an importer crash when the title of an agenda item with an id changed
