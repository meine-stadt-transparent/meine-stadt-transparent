from django.db import models

from .default_fields import DefaultFields
from .parliamentary_group import ParliamentaryGroup
from .person import Person


class ParliamentaryGroupMembership(DefaultFields):
    person = models.ForeignKey(Person)
    parliamentary_group = models.ForeignKey(ParliamentaryGroup)
    start = models.DateField()
    end = models.DateField(null=True, blank=True)
    role = models.CharField(max_length=200)

    def __str__(self):
        return "{}: {}".format(self.person.__str__(), self.parliamentary_group.__str__())
