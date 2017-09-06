from django.db import models

from .body import Body
from .default_fields import DefaultFields
from .legislative_term import LegislativeTerm
from .location import Location


class Committee(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    location = models.ForeignKey(Location, null=True, blank=True)
    legislative_term = models.ForeignKey(LegislativeTerm, blank=True)
    body = models.ForeignKey(Body)
