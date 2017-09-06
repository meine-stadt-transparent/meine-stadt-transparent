from django.db import models
from mainapp.models.default_fields import DefaultFields
from mainapp.models.person import Person


class ParliamentaryGroup(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=20)
    members = models.ManyToManyField(Person)
