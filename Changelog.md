# Changelog

## 0.2.7

 * `manage.py import_json` now by defaults send notifications, this can be disabled with `--no-notify-users`
 * Handle missing elasticsearch or minio more gracefully
 * Fixed an importer crash when the title of an agenda item with an id changed
