from django.db import models

from .default_fields import DefaultFields
from .legislative_term import LegislativeTerm
from .location import Location


class Body(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    center = models.ForeignKey(Location, null=True, blank=True, related_name="body_center")
    outline = models.ForeignKey(Location, null=True, blank=True, related_name="body_outline")
    # There might be e.g. a newer body that didn't exist in the older terms, so
    # bodies and terms are mapped explicitly
    legislative_terms = models.ManyToManyField(LegislativeTerm)
