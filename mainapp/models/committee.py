from django.db import models

from .body import Body
from .default_fields import DefaultFields
from .legislative_term import LegislativeTerm
from .location import Location
from .person import Person


class Committee(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    body = models.ForeignKey(Body)
    location = models.ForeignKey(Location, null=True, blank=True)
    legislative_terms = models.ManyToManyField(LegislativeTerm, blank=True)
    members = models.ManyToManyField(Person, blank=True)
