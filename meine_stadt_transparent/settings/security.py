from meine_stadt_transparent.settings.env import env

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 365 * 24 * 60 * 60
SECURE_HSTS_PRELOAD = True
# There might be deployments where a subdomain is still without https
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)

CSP_DEFAULT_SRC = ("'self'",)

if env.bool("MINIO_REDIRECT", False):
    if env.str("MINIO_PUBLIC_HOST"):
        endpoint = env.str("MINIO_PUBLIC_HOST")
        secure = env.bool("MINIO_PUBLIC_SECURE", True)
    else:
        endpoint = env.str("MINIO_HOST")
        secure = env.bool("MINIO_SECURE", False)

    CSP_DEFAULT_SRC += (("https://" if secure else "http://") + endpoint,)

CSP_SCRIPT_SRC = ("'self'",) + env.tuple("CSP_EXTRA_SCRIPT", default=tuple())
CSP_IMG_SRC = ("'self'", "data:") + env.tuple("CSP_EXTRA_IMG", default=tuple())

if env.str("MAP_TILES_PROVIDER", "OSM") == "OSM":
    CSP_IMG_SRC = CSP_IMG_SRC + (
        "a.tile.openstreetmap.org",
        "b.tile.openstreetmap.org",
        "c.tile.openstreetmap.org",
    )
if env.str("MAP_TILES_PROVIDER", "OSM") == "Mapbox":
    CSP_IMG_SRC = CSP_IMG_SRC + ("api.tiles.mapbox.com", "api.mapbox.com")

SENTRY_HEADER_ENDPOINT = env.str("SENTRY_HEADER_ENDPOINT", None)

CSP_CONNECT_SRC = ("'self'", "sentry.io") + env.tuple(
    "CSP_CONNECT_SRC", default=tuple()
)

if SENTRY_HEADER_ENDPOINT:
    CSP_REPORT_URI = SENTRY_HEADER_ENDPOINT

# Those are not covered by default-src
CSP_FORM_ACTION = ("'self'",)
CSP_FRAME_SRC = ("'self'",) + env.tuple("CSP_FRAME", default=tuple())
CSP_FRAME_ANCESTORS = ("'self'",) + env.tuple("CSP_FRAME", default=tuple())

# Hack for Landshut, where the RIS has a broken ssl configuration (intermediate ceritificate missing)
SSL_NO_VERIFY = env.bool("SSL_NO_VERIFY", False)
