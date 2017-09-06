from django.db import models
from .default_fields import DefaultFields
from .person import Person


class ParliamentaryGroup(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=20)
    members = models.ManyToManyField(Person)
