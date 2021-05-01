from typing import Optional, Dict, Any

from django.db import models
from django.utils.translation import gettext as _
from djgeojson.fields import GeometryField

from .helper import DefaultFields


class Location(DefaultFields):
    description = models.TextField(null=True, blank=True)
    # Unique field to avoid duplicating addresses through location extraction
    # The 767 is a limitation of InnoDB for indexed columns
    # See https://stackoverflow.com/q/1827063/3549270
    search_str = models.CharField(max_length=767, null=True, blank=True, unique=True)

    street_address = models.CharField(max_length=512, null=True, blank=True)
    postal_code = models.CharField(max_length=512, null=True, blank=True)
    locality = models.CharField(max_length=512, null=True, blank=True)
    room = models.CharField(max_length=512, null=True, blank=True)

    is_official = models.BooleanField()
    osm_id = models.BigIntegerField(null=True, blank=True)
    geometry = GeometryField(default=None)

    def __str__(self):
        return self.description or _("Unknown")

    def short(self) -> str:
        """Tries to return a short description of the adress, with a fallback to the long one"""
        if self.street_address and self.room:
            return "{}, {}".format(self.street_address, self.room)
        else:
            return self.description

    def for_maps(self) -> str:
        """Tries to build a good search string for google maps / open street map"""
        if self.street_address:
            if self.postal_code and self.locality:
                return "{}, {} {}".format(
                    self.street_address, self.postal_code, self.locality
                )
            else:
                return self.street_address
        else:
            return self.description

    # noinspection PyUnresolvedReferences
    def coordinates(self) -> Optional[Dict[str, Any]]:
        if self.geometry and self.geometry["type"] == "Point":
            return {
                "lat": self.geometry["coordinates"][1],
                "lon": self.geometry["coordinates"][0],
            }
        else:
            return None
