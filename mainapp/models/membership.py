from django.db import models
from django.urls import reverse

from mainapp.models.helper import DefaultFields
from .organization import Organization
from .person import Person


class Membership(DefaultFields):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)
    role = models.CharField(max_length=200, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    def __str__(self):
        return "{}: {}".format(self.person, self.organization)

    def get_default_link(self):
        return reverse("person", args=[self.person_id])
