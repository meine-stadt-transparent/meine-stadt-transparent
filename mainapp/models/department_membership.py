from django.db import models

from .default_fields import DefaultFields
from .department import Department
from .person import Person


class DepartmentMembership(DefaultFields):
    person = models.ForeignKey(Person)
    department = models.ForeignKey(Department)
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)
    role = models.CharField(max_length=200)

    def __str__(self):
        return "{}: {}".format(self.person.__str__(), self.department.__str__())
