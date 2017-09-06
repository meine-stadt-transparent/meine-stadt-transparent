from django.db import models

from .body import Body
from .default_fields import DefaultFields


class SearchStreet(DefaultFields):
    displayed_name = models.CharField(max_length=1000)
    bodies = models.ManyToManyField(Body, blank=True)
    osm_id = models.BigIntegerField(null=True, blank=True)
    exclude_from_search = models.BooleanField(default=False)
