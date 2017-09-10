from django.db import models

from .default_fields import DefaultFields
from .location import Location
from .paper import Paper


class File(DefaultFields):
    storage_filename = models.CharField(max_length=256)
    displayed_filename = models.CharField(max_length=1000)
    legal_date = models.DateField()
    filesize = models.IntegerField()
    locations = models.ManyToManyField(Location, blank=True)
    paper = models.ForeignKey(Paper, null=True, blank=True)
    parsed_text = models.TextField(null=True, blank=True)
