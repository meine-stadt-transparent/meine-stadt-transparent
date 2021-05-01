from django.db import models
from django.urls import reverse
from django.utils.translation import gettext as _

from .helper import DefaultFields, DummyInterface
from .location import Location


class Person(DefaultFields, DummyInterface):
    name = models.CharField(max_length=100)
    given_name = models.CharField(max_length=100)
    family_name = models.CharField(max_length=100)
    location = models.ForeignKey(
        Location, null=True, blank=True, on_delete=models.CASCADE
    )

    def __str__(self):
        return self.name

    def name_autocomplete(self):
        """A workaround to prevent empty values in the autocomplete-field in elasticsearch, which throws an error"""
        return self.name if len(self.name) > 0 else " "

    def get_default_link(self):
        return reverse("person", args=[self.id])

    def organization_ids(self):
        return [organization.id for organization in self.membership_set.all()]

    def sort_date(self):
        if hasattr(self, "sort_date_prefetch"):
            if self.sort_date_prefetch:
                return self.sort_date_prefetch[0].start
            else:
                return self.created

        # The most recent time this person joined a new organization
        latest = (
            self.membership_set.filter(start__isnull=False).order_by("-start").first()
        )
        if latest:
            return latest.start
        else:
            return self.created

    @classmethod
    def dummy(cls, oparl_id: str) -> "Person":
        return Person(
            name=_("Missing Person"), given_name=_("Missing"), family_name=_("Missing")
        )
