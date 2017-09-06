from django.db import models

from .body import Body
from .default_fields import DefaultFields


class Department(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    body = models.ForeignKey(Body)
