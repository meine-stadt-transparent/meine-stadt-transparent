from django.db import models

from .default_fields import DefaultFields
from mainapp.models import location


class Body(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    center = models.ForeignKey(location.Location, null=True, blank=True, related_name="body_center")
    outline = models.ForeignKey(location.Location, null=True, blank=True, related_name="body_outline")
