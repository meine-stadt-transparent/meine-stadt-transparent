SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

CSP_IMG_SRC = ("'self'", "data:", "api.tiles.mapbox.com", "api.mapbox.com")
# These are covered by default-src, but we need to define them explicitly for extending them later
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'",)
# Those are not covered by default-src
CSP_FORM_ACTION = ("'self'",)
CSP_FRAME_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'self'",)
