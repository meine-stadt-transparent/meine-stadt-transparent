from django.db import models

from .default_fields import DefaultFields
from .meeting import Meeting
from .paper import Paper


class Consultation(DefaultFields):
    """
    See https://github.com/OParl/spec/issues/381 for why we need an extra consultation when there is agenda item
    """
    title = models.TextField(null=True, blank=True)
    meeting = models.ForeignKey(Meeting, null=True, blank=True)
    paper = models.ForeignKey(Paper, null=True, blank=True)
    authoritative = models.NullBooleanField(blank=True)
    # TODO organization = models.ManyToManyField()
    role = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return "{} {}".format(str(self.meeting), str(self.paper))
