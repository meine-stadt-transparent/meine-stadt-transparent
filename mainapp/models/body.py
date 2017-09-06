from django.db import models

from mainapp.models import location
from .default_fields import DefaultFields


class Body(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    center = models.ForeignKey(location.Location, null=True, blank=True, related_name="body_center")
    outline = models.ForeignKey(location.Location, null=True, blank=True, related_name="body_outline")
