from django.db import models
from django.urls import reverse

from .person import Person
from .default_fields import DefaultFields
from .location import Location


class File(DefaultFields):
    name = models.CharField(max_length=200)
    storage_filename = models.CharField(max_length=200)
    displayed_filename = models.CharField(max_length=200)
    # See https://stackoverflow.com/a/643772/3549270#comment11618045_643772
    mime_type = models.CharField(max_length=255)
    legal_date = models.DateField(null=True, blank=True)
    sort_date = models.DateTimeField(auto_now_add=True)
    filesize = models.IntegerField()
    locations = models.ManyToManyField(Location, blank=True)
    mentioned_persons = models.ManyToManyField(Person, blank=True)
    page_count = models.IntegerField(null=True, blank=True)
    parsed_text = models.TextField(null=True, blank=True)
    # In case the license is different than the rest of the system, e.g. a CC-licensed picture
    license = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.displayed_filename

    def rebuild_locations(self, parsed_text):
        from mainapp.functions.document_parsing import extract_locations
        self.locations = extract_locations(parsed_text)

    def coordinates(self):
        coordinates = []
        for location in self.locations.all():
            coordinate = location.coordinates()
            if coordinate:
                coordinates.append(coordinate)

        return coordinates

    def person_ids(self):
        return list(self.mentioned_persons.values_list('id', flat=True))

    def get_default_link(self):
        return reverse('file', args=[self.id])

    def name_autocomplete(self):
        return self.name if len(self.name) > 0 else ' '
