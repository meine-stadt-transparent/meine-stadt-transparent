import inspect

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from mainapp import models

# Register all models using reflections
for name, obj in inspect.getmembers(models):
    if inspect.isclass(obj) and name not in ["DefaultFields"]:
        if issubclass(obj, SimpleHistoryAdmin):
            admin.site.register(obj, admin_class=SimpleHistoryAdmin)
        else:
            admin.site.register(obj)
