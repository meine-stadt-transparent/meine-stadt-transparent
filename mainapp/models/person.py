from django.db import models
from mainapp.models.default_fields import DefaultFields
from mainapp.models.location import Location


class Person(DefaultFields):
    name = models.CharField(max_length=100)
    given_name = models.CharField(max_length=50)
    family_name = models.CharField(max_length=50)
    location = models.ForeignKey(Location, null=True)
