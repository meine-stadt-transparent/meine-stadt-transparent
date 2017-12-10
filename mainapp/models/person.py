import re

from django.db import models
from django.urls import reverse
from django.conf import settings

from .default_fields import DefaultFields
from .location import Location


class Person(DefaultFields):
    name = models.CharField(max_length=100)
    given_name = models.CharField(max_length=50)
    family_name = models.CharField(max_length=50)
    location = models.ForeignKey(Location, null=True, blank=True)

    def __str__(self):
        return self.name_without_salutation()

    def name_autocomplete(self):
        """ A workaround to prevent empty values in the autocomplete-field in elasticsearch, which throws an error """
        return self.name if len(self.name) > 0 else ' '

    def get_default_link(self):
        return reverse('person', args=[self.id])

    def name_without_salutation(self):
        name = self.name
        for prefix in settings.SITE_STRIP_NAME_SALUTATIONS:
            name = re.sub(r"^" + re.escape(prefix) + " ", "", name)
        return name
