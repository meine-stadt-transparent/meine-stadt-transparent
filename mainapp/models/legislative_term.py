from django.db import models

from .helper import DefaultFields, ShortableNameFields


class LegislativeTerm(DefaultFields, ShortableNameFields):
    start = models.DateField()
    end = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.short_name
