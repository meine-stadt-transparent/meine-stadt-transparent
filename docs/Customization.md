# Configuration

We try to determine as much as possible automatically, but some things must be set manually. For some functionality we also rely on external web services. Most of them are optional, but can improve the quality and reliability of this system. To use them, you will need to create an account and set the credentials in the ``.env``file.

We highly recommend configuring at least mailjet, mapbox and opencage.

## Required

 * `REAL_HOST`: The url of the website, e.g. `meine-stadt-transparent.de`
 * `SECRET_KEY`: A unique, secret string of random characters
 * `ELASTICSEARCH_URL`: This is normally either `elasticsearch:9200` with docker compose or `localhost:9200` otherwise.
 * `MINIO_HOST`: This is normally either `minio:9000` with docker compose and `localhost:9000` otherwise.
 * `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` are the username and password equivalent for minio, with must match the values you started minio with.
 * `STATIC_ROOT`: Location where the static files are. This defaults to `static` in the project root, which is correct without docker, but has to be set to `/static` with docker.

## Recommended

 * `SITE_NAME`: Used as name of the website in various place, e.g. in the site title or in emails. Defaults to "Meine Stadt Transparent".
 * `SITE_DEFAULT_ORGANIZATION`: The database id of the organization representing the city council. The easiest way to find it is to look through the organization list and take the id from the url of the organization's page.

### E-Mail

By default, we send e-mails using djangos built in SMTP sending. Configure SMTP server and credentials by setting the [`EMAIL_URL`](https://github.com/joke2k/django-environ/blob/b32c07d7ed57cdeaef246f995a29e5fe39a076b3/README.rst#supported-types) environment key.

[Mailjet](https://dev.mailjet.com/) can be set up as an alternative for sending e-mails. Add `MAIL_PROVIDER=Mailjet` and set `MAILJET_API_KEY` and `MAILJET_SECRET_KEY` to your keys.

The e-mail-configuration can be tested using the following command line call, which sends a test e-mail to the given e-mail-address:

```
./manage.py test-email test@example.org
```

### User management

User management requires a valid E-Mail configuration. If you want to hide links to register/sign in, set `ACCOUNT_MANAGEMENT_VISIBLE=False`.

### Map tiles

By default, the map uses the tiles provided by [OpenStreetMap](https://wiki.openstreetmap.org/wiki/Standard_tile_layer). However, for production use, it is recommended to use another provider. For now, we support [Mapbox](https://www.mapbox.com/). To use it, you need to sign up for an account, choose a map style (default is fine) and add the following information to the ``.env``-file:

```
MAP_TILES_PROVIDER=Mapbox
MAPBOX_TOKEN=pk....
MAP_TILES_URL=https://api.mapbox.com/styles/v1/username/stylename/tiles/256/{z}/{x}/{y}{highres}?access_token={accessToken}
```

### Geocoding

By default, we use [Nominatim](https://wiki.openstreetmap.org/wiki/Nominatim) to resolve addresses to coordinates. You can switch to [OpenCage Geocoder](https://geocoder.opencagedata.com/), by adding your key as `OPENCAGE_KEY` and setting `GEOEXTRACT_ENGINE` to "OpenCage", or you can switch to [Mapbox](TODO) by setting `GEOEXTRACT_ENGINE` to "Mapbox" and setting `MAPBOX_TOKEN` (same as for the maps).

## Determined by the importer

The oparl importer should tell you the values for those options.

  * `SITE_DEFAULT_BODY`: The database id of the body that represents the current city. Defaults to 1 which is correct when you have only imported one body.

## Overriding templates and styles

You can easily override templates and add custom styles, e.g. for matching the corporate design of a specific city.

Two examples are bundled with this repository:
- [juelich_transparent](../customization_examples/juelich_transparent): Only the [contact form](../mainapp/templates/info/contact.html) is overridden
- [bedburg_transparent](../customization_examples/bedburg_transparent): The contact form is overriden and a custom style sheet is provided.

You can easily add your own customizations by putting them into a folder inside the `customization` folder. Copying over one of the examples should by a good starting point.

To override templates, set `TEMPLATE_DIRS` in ``.env`` to the ``templates``-folder within the city directory, e.g. ``TEMPLATE_DIRS=customization/juelich_transparent/templates``

The following parts are required to change styles or javascript:
  - A ``webpack.config.js`` file registering an entry point for Webpack. The entry point needs to point to a js-File. Note that the paths in that file are realtive to [etc](../etc).
  - The js File, usually ``assets/js/mycity-main.js``. This file includes the main SCSS file with an ES6 import.
  - The SCSS-File, usually ``assets/css/mainapp-mycity.scss``. This file includes the main [mainapp.scss](../mainapp/assets/css/mainapp.scss), but can define its own variables and styles as well. It will be compiled to a regular CSS file of the same base filename.
  - The new CSS-File needs to be registered in the ``.env``-file, e.g. ``TEMPLATE_MAIN_CSS=mainapp-mycity``
  - If you want to use translations, create a `locale` folder first (https://stackoverflow.com/a/24937512/3549270).

Hints:
 - Do not modify our files without creating a pull request. You'll have huge problems updating otherwise. Also put your files in a version control system (i.e. git).
 - Keep the name of the export, the name of the main js file and the name of the main scss file identical to avoid confusion.
 - templates are written in the [django template language](https://docs.djangoproject.com/en/2.1/topics/templates/#the-django-template-language).
 - Localization does also work for custom templates. With `./manage.py makemessages -a` you create or update into a file called `locale/de/LC_MESSAGES/django.po` in your custom folder. Translate your strings there and compile them with `./manage.py compilemessages --locale de`.

### Embedding external resources / CSP

If you modify templates as described above and want to embed resources hosted on another domain (for example to embed images, web-fonts, or a tracking tool), you have to whitelist the used domains, as our Content Security Policy ([CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)) will prevent them from being loaded otherwise. The following configuration settings are supported for that reason:

```
CSP_EXTRA_SCRIPT=www.example.org,'sha256-QOPA8zHkrz5+pN4Af9GXK6m6mW7STjPY13tS3Z3xLTU=' # The latter one is for whitelisting inline-scripts
CSP_EXTRA_IMG=www.example.org
```

## Other External Services

### Social login

To spare the user the hassle of creating and confirming a new account just for this site, we support social login, currently through twitter and facebook.

To enable login via twitter or facebook, create an app in the corresponding developer portal. See the [AllAuth-Page](http://django-allauth.readthedocs.io/en/latest/providers.html#facebook) for details.

For twitter, you'll also need [https://stackoverflow.com/a/32852370/3549270](https://stackoverflow.com/a/32852370/3549270) or users will be prompted to enter an email adress after login.

For facebook, you'll need to go to `https://developers.facebook.com/apps/[your app id]/fb-login/settings/` and add the site's url in "valid oauth redirect urls".

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

### Microsoft Azure: OCR

This is optional if you want to use OCR for extracting the text of scanned documents. Set up a Azure account and add a [Computer Vision](https://azure.microsoft.com/en-us/try/cognitive-services/?api=computer-vision) Resource (part of Cognitive Services). Add the API Key to the `.env` file as `OCR_AZURE_KEY`.

### Error reporting

You can use [Sentry](https://sentry.io) as error tracking service by setting `SENTRY_DSN`. Optionally set `SENTRY_HEADER_ENDPOINT` to collect csp violations. If you want help us, please ask us for a dsn from our account, so we can keep track of real world errors.

### Tracking

You add a tracker by overwriting the template `templates/partials/base_footer_extra.html` and adding the javascript in there. See `juelich_transparent` for a customization example with matomo (formerly piwik).

## Localization

Meine Stadt Transparent is fully internationalized with German translations maintained by us and all defaults set for Germany. If you want to use it with any other locale, you need to create translations (except for english, of course) and change the following options:

 * `LANGUAGE_CODE`: Defaults to "de-de"
 * `TIME_ZONE`: Defaults to "Europe/Berlin"
 * `ELASTICSEARCH_LANG`: Texts in different languages need different preprocessing. Defaults to "german"
 * `CITY_AFFIXES`: Often the data we get contains additional information in city names, e.g. "Landdeshauptstadt München" instead of "München", which we need to cut away. `CITY_AFFIXES` contains a list of those prefixes in German, currently "Stadt", "Landeshauptstadt", "Gemeinde", "Kreisverwaltung", "Landkreis" and "Kreis.
 * `DISTRICT_REGEX`: Sometimes, there's a city and a district of the same name. Those are disambiguated by checking whether the name matches this regex. Defaults to "(^| )kreis|kreis( |$)"
 * `GEOEXTRACT_SEARCH_COUNTRY`: Sets the country for the geocoding service. Defaults to "Deutschland"
  * `GEOEXTRACT_LANGUAGE`: Language passed to geopy for geocoding, defaults to the first part of `LANGUAGE_CODE`, i.e. "de"

## Various

 * `CALENDAR_DEFAULT_VIEW`: Possible values: `month`, `listYear`, `listMonth`, `listDay`, `basicWeek`, `basicDay`, `agendaWeek`, `agendaDay`
 * `CALENDAR_HIDE_WEEKENDS`: Whether the week and month view of the calendar should include weekends. Defaults to true.
 * `CALENDAR_MIN_TIME` and `CALENDAR_MAX_TIME`: In the day view, only this part of the day is shown. Defaults to "08:00:00" and "21:00:00".
 * `CSP_EXTRA_SCRIPT` and `CSP_EXTRA_IMG`: Add values to the script src and image src csp directive, e.g. for loading matomo scripts.
 * `ELASTICSEARCH_PREFIX`: The elasticsearch indices used by Meine Stadt Transparent will be prefixed by this. Defaults to "meine-stadt-transparent"
 * `ELASTICSEARCH_QUERYSET_PAGINATION`: The batch size for the elasticsearch indexing. See [django-elasticsearch-dsl docs](https://django-elasticsearch-dsl.readthedocs.io/en/latest/quickstart.html?highlight=queryset_pagination#declare-data-to-index) for details.
 * `ELASTICSEARCH_TIMEOUT`: Timeout in seconds for the elasticsearch client for indexing.
 * `MINIO_PREFIX`: All minio bucket names will be prefixed with this string. Default to "meine-stadt-transparent-"
  * `CUSTOM_IMPORT_HOOKS`: Used to hook up your own code with the default importer. See the readme for usage details.
 * `EMAIL_FROM` and `EMAIL_FROM_NAME`: Sender address and name for notifications. Defaults to `info@REAL_HOST` and `SITE_NAME`
 * `EMBED_PARSED_TEXT_FOR_SCREENREADERS`: pdfs are really bad for blind people, so this includes the plain text of PDFs next to the PDF viewer, visible only for Screenreaders. On by default to improve accessibility, deactivatable in case there are legal concerns.
 * `FILE_DISCLAIMER`: This is a small text shown below every document to tell people we're not the original publisher of that document. `FILE_DISCLAIMER_URL` is shown as link next to the
 * `OCR_AZURE_KEY`: [Azure](https://azure.microsoft.com) has an ocr service with high accuracy. Since it's pay-per-use, it must be manually used through `./manage.py ocr-file`. If you want to use azure, set `OCR_AZURE_KEY` to your api key. You can also set `OCR_AZURE_LANGUAGE`, which defaults to `de` for German, and `OCR_AZURE_API`, which
`SEARCH_PAGINATION_LENGTH`
 * `SECURE_HSTS_INCLUDE_SUBDOMAINS`: Sets the include subdomains option in the hsts header we send. Deactivatable if you have legacy services running on subdomains.
 * `SITE_SEO_NOINDEX`: Set this to true to hide the site from the google index.
 * `TEMPLATE_DIRS`: Allows customization by overriding templates. See the readme for more details.
 * `TEXT_CHUNK_SIZE`: Our location extraction library fails with big inputs (see https://github.com/stadt-karlsruhe/geoextract/issues/7). That's why we split the text before analysing it, by default into 1MB chunks.
 * `NO_LOG_FILES`: Don't create any actual log files, only log to stdout/stderr. Useful when working with docker and log aggregation.

## Appendix

Even though it's possible to change those, you shouldn't need change them in production.

 * `DEBUG`: Should always be `False` in production
 * `DEBUG_STYLES`: Adds 'unsafe-inline' to the style src csp making it easier to use your browser's developer tools
 * `DEBUG_TESTING`: Makes chromedriver open an actual chrome window
 * `DJANGO_LOG_LEVEL`, `MAINAPP_LOG_LEVEL` and `IMPORTER_LOG_LEVEL`: Overrides the default log level for that component.
 * `LOG_DIRECTORY`: The directory in which the log files will be created. Ignored if `NO_LOG_FILES` is set.
 * `ENABLE_PGP` and `SKS_KEYSERVER`: While support pgp encrypted notifications with a UI for selecting the key from an sks keyserver, this feature is disabled by default because encrypted notifications end up as plain text which breaks our UX. Before you can enable it, you need to run `poetry install --extras pgp`.
 * `OPARL_INDEX`: Used to determine the oparl body id based on the city name by searching for a body with a fitting name in the [oparl mirror](https://politik-bei-uns.de/info/schnittstelle) of [Politik bei Uns](https://politik-bei-uns.de/).
 * `ELASTICSEARCH_ENABLED`: Allows to disable elasticsearch for development or test environment
 * `ABSOLUTE_URI_BASE`: This url is used as base when relative urls are not an option and we can't get the real url from the user's http requests, e.g. when generating notifications. Defaults to `"https://" + REAL_HOST`
 * `ORGANIZATION_ORDER`: Fine tune in the order in which the organizations are shown in the overview page.
 * `ALLOWED_HOSTS`: [docs](https://docs.djangoproject.com/en/2.1/ref/settings/#allowed-hosts)
 * `PRODUCT_NAME`: Set to "Meine Stadt Transparent". Used e.g. as user agent.
 * `SECURE_HSTS_INCLUDE_SUBDOMAINS`: Wether to include subdomains in the hsts header. Defaults to true.
