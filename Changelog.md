# Changelog

## 0.2.8

 * Both importer now have a better heuristics for determining the date of a paper. Additionally, the result order should now be more reasonable.
 * Updated the json importer to format version 3
 * Fixed a regression with meeting without end from 0.2.7
 * The ics export has an html description (which is used e.g. by google calendar and outlook) which includes a link to the meeting.

## 0.2.7

 * `manage.py import_json` now by defaults send notifications, this can be disabled with `--no-notify-users`
 * Handle missing elasticsearch or minio more gracefully
 * Fixed an importer crash when the title of an agenda item with an id changed
