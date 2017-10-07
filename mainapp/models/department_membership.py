from django.db import models

from .department import Department
from .generic_membership import GenericMembership


class DepartmentMembership(GenericMembership):
    department = models.ForeignKey(Department)

    def __str__(self):
        return "{}: {}".format(self.person.__str__(), self.department.__str__())
