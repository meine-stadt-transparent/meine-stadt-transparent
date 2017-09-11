from django.db import models

from .body import Body
from .default_fields import DefaultFields
from .legislative_term import LegislativeTerm
from .location import Location


class Committee(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    body = models.ForeignKey(Body)
    start = models.DateField()
    end = models.DateField()
    legislative_terms = models.ManyToManyField(LegislativeTerm, blank=True)
    location = models.ForeignKey(Location, null=True, blank=True)

    def __str__(self):
        return self.short_name
