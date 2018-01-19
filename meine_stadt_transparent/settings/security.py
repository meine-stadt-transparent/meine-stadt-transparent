SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 365 * 24 * 60 * 60
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

CSP_IMG_SRC = ("'self'", "data:", "api.tiles.mapbox.com", "api.mapbox.com")
# These are covered by default-src, but we need to define them explicitly for extending them later
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'",)
# Those are not covered by default-src
CSP_FORM_ACTION = ("'self'",)
CSP_FRAME_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'self'",)
