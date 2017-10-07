from django.db import models

from .generic_membership import GenericMembership
from .parliamentary_group import ParliamentaryGroup


class ParliamentaryGroupMembership(GenericMembership):
    parliamentary_group = models.ForeignKey(ParliamentaryGroup)

    def __str__(self):
        return "{}: {}".format(self.person.__str__(), self.parliamentary_group.__str__())
