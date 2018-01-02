import inspect

from django.contrib import admin

from mainapp import models

# Register all models using reflections
for name, obj in inspect.getmembers(models):
    if inspect.isclass(obj) and name not in ["DefaultFields", "GenericMembership"]:
        admin.site.register(obj)
