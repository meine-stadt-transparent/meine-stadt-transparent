from meine_stadt_transparent.settings.env import *

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
if not TESTING:
    SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 365 * 24 * 60 * 60
SECURE_HSTS_PRELOAD = True
# There might be deployments where a subdomain is still without https
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)

CSP_IMG_SRC = ("'self'", "data:", "api.tiles.mapbox.com", "api.mapbox.com")
# Those are not covered by default-src
CSP_FORM_ACTION = ("'self'",)
CSP_FRAME_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'self'",)
