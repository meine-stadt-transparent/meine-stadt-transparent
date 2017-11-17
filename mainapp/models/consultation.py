from django.db import models

from .default_fields import SoftDeleteModelManager, SoftDeleteModelManagerWithDeleted
from .meeting import Meeting
from .paper import Paper


class Consultation(models.Model):
    """
    See https://github.com/OParl/spec/issues/381 for why we need an extra consultation when there is agenda item
    """
    oparl_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    title = models.TextField(null=True, blank=True)
    meeting = models.ForeignKey(Meeting)
    paper = models.ForeignKey(Paper, null=True, blank=True)
    authoritative = models.NullBooleanField(blank=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)
    # TODO: Modelling the resolution which can be both file and plain text

    objects = SoftDeleteModelManager()
    objects_with_deleted = SoftDeleteModelManagerWithDeleted()

    def __str__(self):
        return "{} {}".format(self.title, self.meeting.__str__())
