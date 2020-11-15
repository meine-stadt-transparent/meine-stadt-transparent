from django.db import models

from .body import Body
from .helper import DefaultFields


class SearchStreet(DefaultFields):
    displayed_name = models.CharField(max_length=1000)
    body = models.ForeignKey(Body, blank=True, null=True, on_delete=models.CASCADE)
    osm_id = models.BigIntegerField(null=True, blank=True, unique=True)
    exclude_from_search = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["osm_id"])]
