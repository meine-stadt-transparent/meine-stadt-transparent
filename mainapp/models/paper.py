from django.db import models

from .committee import Committee
from .default_fields import DefaultFields
from .department import Department
from .parliamentary_group import ParliamentaryGroup
from .person import Person


class Paper(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    submitter_parliamentary_group = models.ManyToManyField(ParliamentaryGroup)
    submitter_committee = models.ManyToManyField(Committee)
    submitter_department = models.ManyToManyField(Department)
    # Only relevant if a person acts independently from one of the submitting organizations
    submitter_persons = models.ManyToManyField(Person)
    # There isn't any logic built on change requests, so higher order change requests are allowed
    is_change_request_of = models.ForeignKey("self", null=True, blank=True)

