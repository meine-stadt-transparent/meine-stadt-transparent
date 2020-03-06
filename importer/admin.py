from django.contrib import admin

from importer.models import CachedObject, ExternalList

admin.site.register(CachedObject)
admin.site.register(ExternalList)
