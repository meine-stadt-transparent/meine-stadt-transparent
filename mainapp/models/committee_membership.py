from django.db import models

from .committee import Committee
from .generic_membership import GenericMembership


class CommitteeMembership(GenericMembership):
    committee = models.ForeignKey(Committee)

    def __str__(self):
        return "{}: {}".format(self.person.__str__(), self.committee.__str__())
