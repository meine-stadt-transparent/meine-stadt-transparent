from django.db import models

from .body import Body
from .default_fields import DefaultFields
from .legislative_term import LegislativeTerm
from .location import Location


class ParliamentaryGroup(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    # start and end shouldn't be nullable, but e.g. München Transparent doesn't have this data
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)
    body = models.ForeignKey(Body, related_name='parliamentarygroup')
    legislative_terms = models.ManyToManyField(LegislativeTerm, blank=True)
    location = models.ForeignKey(Location, null=True, blank=True)

    def __str__(self):
        return self.short_name

