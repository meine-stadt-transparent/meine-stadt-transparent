import re

from django.conf import settings
from django.db import models
from django.urls import reverse

from .default_fields import DefaultFields
from .location import Location


class Person(DefaultFields):
    name = models.CharField(max_length=100)
    given_name = models.CharField(max_length=50)
    family_name = models.CharField(max_length=50)
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    def name_autocomplete(self):
        """ A workaround to prevent empty values in the autocomplete-field in elasticsearch, which throws an error """
        return self.name if len(self.name) > 0 else ' '

    def get_default_link(self):
        return reverse('person', args=[self.id])

    def organization_ids(self):
        return list(self.organizationmembership_set.values_list('organization_id', flat=True))

    def sort_date(self):
        # The most recent time this person joined a new organization
        latest = self.organizationmembership_set.filter(start__isnull=False).order_by('-start').first()
        if latest:
            return latest.start
        else:
            return self.created
