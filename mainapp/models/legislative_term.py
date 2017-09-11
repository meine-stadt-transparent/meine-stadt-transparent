from django.db import models

from .default_fields import DefaultFields


class LegislativeTerm(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=200)
    start = models.DateField()
    end = models.DateField()

    def __str__(self):
        return self.short_name
