import inspect

from django.contrib import admin

from mainapp import models

# Register all models using reflections
for name, obj in inspect.getmembers(models):
    if inspect.isclass(obj) and not name == "DefaultFields":
        admin.site.register(obj)


