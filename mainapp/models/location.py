from django.db import models

from .body import Body
from .default_fields import DefaultFields


class Location(DefaultFields):
    displayed_name = models.CharField(max_length=1000)
    description = models.TextField()
    body = models.ManyToManyField(Body)
    is_official = models.BooleanField()
    osm_id = models.BigIntegerField(null=True, blank=True)

