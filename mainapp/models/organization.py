from django.db import models
from django.urls import reverse
from django.utils.translation import pgettext as _

from .body import Body
from .default_fields import DefaultFields
from .legislative_term import LegislativeTerm
from .location import Location
from .organization_type import OrganizationType

ORGANIZATION_TYPE_NAMES = {
    "parliamentary group": _('Document Type Name', 'Parliamentary Group'),
    "committee": _('Document Type Name', 'Committee'),
    "department": _('Document Type Name', 'Deparment'),
    "organization": _('Document Type Name', 'Organization'),
}


class Organization(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)
    body = models.ForeignKey(Body)
    legislative_terms = models.ManyToManyField(LegislativeTerm, blank=True)
    location = models.ForeignKey(Location, null=True, blank=True)
    # html color without the hash
    color = models.CharField(max_length=6, null=True, blank=True)
    logo = models.CharField(max_length=255, null=True, blank=True)
    organization_type = models.ForeignKey(OrganizationType)

    def __str__(self):
        return self.short_name

    # A workaround to prevent empty values in the autocomplete-field in elasticsearch, which throws an error
    def name_autocomplete(self):
        return self.name if len(self.name) > 0 else ' '

    def get_default_link(self):
        return reverse('organization', args=[self.id])
