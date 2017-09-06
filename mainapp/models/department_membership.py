from django.db import models

from .default_fields import DefaultFields
from .department import Department
from .person import Person


class CommitteeMembership(DefaultFields):
    person = models.ForeignKey(Person)
    department = models.ForeignKey(Department)
    start = models.DateField()
    end = models.DateField()
    role = models.CharField(max_length=200)
