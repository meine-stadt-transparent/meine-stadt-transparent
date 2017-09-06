from django.db import models

from .default_fields import DefaultFields
from .legislative_term import LegislativeTerm
from .location import Location


class Committee(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    location = models.ForeignKey(Location, null=True)
    legislative_term = models.ForeignKey(LegislativeTerm)