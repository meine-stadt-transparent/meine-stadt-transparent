from django.db import models

from .default_fields import DefaultFields
from .person import Person
from .parliamentary_group import ParliamentaryGroup
from .committee import Committee
from .department import Department


class Paper(DefaultFields):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    submitter_parliamentary_group = models.ManyToManyField(ParliamentaryGroup)
    submitter_committee = models.ManyToManyField(Committee)
    submitter_department = models.ManyToManyField(Department)
    # Only relevant if a person acts independently from one of the submitting organizations
    submitter_persons = models.ManyToManyField(Person)
    # There isn't any logic built on change requests, so higher order change requests are allowed
    is_change_request_of = models.ForeignKey("self", null=True, blank=True)

