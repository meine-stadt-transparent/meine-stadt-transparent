from django.db import models

from .committee import Committee
from .default_fields import DefaultFields
from .person import Person


class CommitteeMembership(DefaultFields):
    person = models.ForeignKey(Person)
    committee = models.ForeignKey(Committee)
    start = models.DateField()
    end = models.DateField()
    role = models.CharField(max_length=200)
