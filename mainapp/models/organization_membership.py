from django.db import models

from mainapp.models.default_fields import DefaultFields
from .person import Person
from .organization import Organization


class OrganizationMembership(DefaultFields):
    person = models.ForeignKey(Person)
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)
    role = models.CharField(max_length=200)
    organization = models.ForeignKey(Organization)

    def __str__(self):
        return "{}: {}".format(self.person.__str__(), self.organization.__str__())
