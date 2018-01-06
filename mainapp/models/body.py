from django.conf import settings
from django.db import models
from django.urls import reverse

from .default_fields import DefaultFields, ShortableNameFields
from .legislative_term import LegislativeTerm
from .location import Location


class Body(DefaultFields, ShortableNameFields):
    center = models.ForeignKey(Location, null=True, blank=True, related_name="body_center", on_delete=models.CASCADE)
    outline = models.ForeignKey(Location, null=True, blank=True, related_name="body_outline", on_delete=models.CASCADE)
    # There might be e.g. a newer body that didn't exist in the older terms, so
    # bodies and terms are mapped explicitly
    legislative_terms = models.ManyToManyField(LegislativeTerm, blank=True)

    def __str__(self):
        return self.short_name

    def get_default_link(self):
        if settings.SITE_DEFAULT_BODY == self.id:
            return reverse('index')
        else:
            return reverse('body', args=[self.id])
