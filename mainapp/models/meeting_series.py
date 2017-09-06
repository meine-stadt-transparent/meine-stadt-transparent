from django.db import models

from .default_fields import DefaultFields


class MeetingSeries(DefaultFields):
    name = models.CharField(max_length=1000)
    description = models.TextField(null=True, blank=True)
    # This is true for meetings that are e.g. held once a month
    is_regular = models.BooleanField()
