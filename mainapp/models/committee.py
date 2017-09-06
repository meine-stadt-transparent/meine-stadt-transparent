from django.db import models

from mainapp.models.default_fields import DefaultFields
from mainapp.models.legislative_term import LegislativeTerm
from mainapp.models.location import Location


class Committee(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    location = models.ForeignKey(Location, null=True)
    legislative_term = models.ForeignKey(LegislativeTerm)