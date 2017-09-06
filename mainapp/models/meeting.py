from django.db import models
from mainapp.models.default_fields import DefaultFields
from mainapp.models.location import Location


class Meeting(DefaultFields):
    name = models.CharField(max_length=1000)
    cancelled = models.BooleanField()
    start = models.DateTimeField()
    end = models.DateTimeField()
    location = models.ForeignKey(Location, null=True)
