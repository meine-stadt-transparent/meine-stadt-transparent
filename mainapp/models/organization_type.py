from django.db import models

from .body import Body
from .default_fields import DefaultFields
from .legislative_term import LegislativeTerm
from .location import Location


class OrganizationType(models.Model):
    name = models.CharField(max_length=200, null=True)  # Null represents the unknown type

    def __str__(self):
        return self.name
