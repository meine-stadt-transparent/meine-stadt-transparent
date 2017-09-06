from django.db import models

from .default_fields import DefaultFields


class Paper(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
