from django.db import models
from django.utils.translation import ugettext as _
from djgeojson.fields import GeometryField

from .default_fields import DefaultFields


class Location(DefaultFields):
    short_description = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    # Need to work around a cyclic import here
    bodies = models.ManyToManyField("mainapp.Body", blank=True)
    is_official = models.BooleanField()
    osm_id = models.BigIntegerField(null=True, blank=True)
    geometry = GeometryField(default=None)

    def __str__(self):
        return self.short_description or self.description or _("Unknown")

    def coordinates(self):
        if self.geometry and self.geometry['type'] == 'Point':
            return {
                "lat": self.geometry['coordinates'][1],
                "lon": self.geometry['coordinates'][0],
            }
        else:
            return None
