from django.db import models

from .default_fields import SoftDeleteModelManager, SoftDeleteModelManagerWithDeleted
from .meeting import Meeting
from .paper import Paper


class AgendaItem(models.Model):
    oparl_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    key = models.CharField(max_length=20)
    title = models.TextField()
    meeting = models.ForeignKey(Meeting)
    # The agenda items of a meeting are ordered by this field
    position = models.IntegerField()
    public = models.NullBooleanField(blank=True)
    paper = models.ForeignKey(Paper, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)
    # TODO: Modelling the resolution which can be both file and plain text

    objects = SoftDeleteModelManager()
    objects_with_deleted = SoftDeleteModelManagerWithDeleted()

    def __str__(self):
        return "{} {} ({}. {})".format(self.key, self.title, self.position, self.meeting.__str__())

    class Meta:
        ordering = ["meeting", "position"]
