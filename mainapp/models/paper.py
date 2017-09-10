from django.db import models

from .committee import Committee
from .default_fields import DefaultFields
from .department import Department
from .parliamentary_group import ParliamentaryGroup
from .person import Person


class Paper(DefaultFields):
    reference_number = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    submitter_parliamentary_group = models.ManyToManyField(ParliamentaryGroup, blank=True)
    submitter_committee = models.ManyToManyField(Committee, blank=True)
    submitter_department = models.ManyToManyField(Department, blank=True)
    # Only relevant if a person acts independently from one of the submitting organizations
    submitter_persons = models.ManyToManyField(Person, blank=True)
    # There isn't any logic built on change requests, so higher order change requests are allowed
    is_change_request_of = models.ForeignKey("self", null=True, blank=True)

    def __str__(self):
        return self.short_name
