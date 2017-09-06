from django.db import models

from .default_fields import DefaultFields
from .parliamentary_group import ParliamentaryGroup
from .person import Person


class ParliamentaryGroupMembership(DefaultFields):
    person = models.ForeignKey(Person)
    parliamentary_group = models.ForeignKey(ParliamentaryGroup)
    start = models.DateField()
    end = models.DateField()
    role = models.CharField(max_length=200)
