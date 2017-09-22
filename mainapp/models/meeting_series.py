from django.db import models

from .default_fields import DefaultFields


class MeetingSeries(DefaultFields):
    name = models.CharField(max_length=1000)
    short_name = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    # This is true for meetings that are e.g. held once a month
    is_regular = models.BooleanField()

    def __str__(self):
        return self.name

