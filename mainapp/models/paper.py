from typing import Generator

from django.db import models
from django.urls import reverse

from .file import File, fallback_date
from .helper import DefaultFields, ShortableNameFields
from .organization import Organization
from .paper_type import PaperType
from .person import Person


class Paper(DefaultFields, ShortableNameFields):
    reference_number = models.CharField(max_length=50, null=True, blank=True)
    organizations = models.ManyToManyField(Organization, blank=True)
    # Only relevant if a person acts independently from one of the submitting organizations
    persons = models.ManyToManyField(Person, blank=True)
    # There isn't any logic built on change requests, so higher order change requests are allowed
    change_request_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE
    )

    # We store three kinds of dates with decreasing quality:
    # * legal_date: The official date, which is e.g. used for deadlines.
    #   This does not necessarily match the date of publication.
    #   Unfortunately it's often not available.
    # * display_date: This date is either the legal_date or the date of the
    #   first consultation. We consider it good enough to be shown to the user
    # * sort_date: This always has a value which is potentially really wrong.
    #   Only used in the search
    legal_date = models.DateField(null=True, blank=True)
    display_date = models.DateField(null=True, blank=True)
    sort_date = models.DateTimeField(default=fallback_date)

    main_file = models.ForeignKey(
        File,
        null=True,
        blank=True,
        related_name="paper_main_file",
        on_delete=models.CASCADE,
    )
    files = models.ManyToManyField(File, blank=True)
    paper_type = models.ForeignKey(
        PaperType, null=True, blank=True, on_delete=models.CASCADE
    )

    def all_files(self) -> Generator[File, None, None]:
        if self.main_file:
            yield self.main_file
        for file in self.files.all():
            yield file

    def get_autocomplete(self):
        if self.name and self.reference_number:
            return self.name + " " + self.reference_number
        elif self.name:
            return self.name
        else:
            return " "

    def __str__(self):
        return self.short_name

    def get_default_link(self):
        return reverse("paper", args=[self.id])

    def person_ids(self):
        """This is actually efficient due to the prefetch"""
        return [person.id for person in self.persons.all()]

    def organization_ids(self):
        return [organization.id for organization in self.organizations.all()]

    def files_ordered(self):
        """Since we don't have an intended order of the non-main file files, we sort them alphabetically"""
        return self.files.order_by("name")

    class Meta:
        indexes = [models.Index(fields=["-sort_date"])]
