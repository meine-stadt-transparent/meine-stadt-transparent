from django.db import models

from .default_fields import DefaultFields
from .location import Location
from .paper import Paper


class File(DefaultFields):
    storage_filename = models.CharField(max_length=256)
    displayed_filename = models.CharField(max_length=256)
    legal_date = models.DateField()
    filesize = models.IntegerField()
    locations = models.ManyToManyField(Location, blank=True)
    paper = models.ForeignKey(Paper, null=True, blank=True)
    parsed_text = models.TextField(null=True, blank=True)
    # In case the license is different than the rest of the system, e.g. a CC-licensed picture
    license = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.displayed_filename

    def rebuild_locations(self):
        from mainapp.functions.document_parsing import extract_locations
        locations = extract_locations(self.parsed_text)
        self.locations.clear()
        for location in locations:
            self.locations.add(location)
