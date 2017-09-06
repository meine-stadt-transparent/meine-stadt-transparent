from django.db import models
from .default_fields import DefaultFields


class Location(DefaultFields):
    displayed_name = models.CharField(max_length=1000)
    description = models.TextField()

