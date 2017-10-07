from django.db import models

from .default_fields import DefaultFields
from .person import Person


class GenericMembership(DefaultFields):
    person = models.ForeignKey(Person)
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)
    role = models.CharField(max_length=200)

    class Meta:
        abstract = True
